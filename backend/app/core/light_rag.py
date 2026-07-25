import os
import asyncio
import numpy as np
from typing import Optional
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete
from lightrag.llm.gemini import gemini_embed
from lightrag.utils import wrap_embedding_func_with_attrs
from app.core.config import settings

# --- Working directory for LightRAG storage (local file-based KG) ---
LIGHTRAG_WORKING_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "lightrag_data"
)
os.makedirs(LIGHTRAG_WORKING_DIR, exist_ok=True)


# =====================================================================
# 1. Custom LLM function: Groq (OpenAI-compatible endpoint)
# =====================================================================
async def groq_llm_complete(
    prompt: str,
    system_prompt: Optional[str] = None,
    history_messages: list = [],
    **kwargs,
) -> str:
    """
    Calls Groq's OpenAI-compatible API via LightRAG's built-in
    openai_complete helper, just pointing to Groq's base URL.
    """
    # Filter out kwargs that openai_complete doesn't accept
    # but keep hashing_kv which is now required by lightrag
    filtered_kwargs = {k: v for k, v in kwargs.items() if k not in [
        "keyword_extraction", "model",
    ]}
    return await openai_complete(
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        **filtered_kwargs,
    )


# =====================================================================
# 2. Custom Embedding function: Google Gemini text-embedding-004
# =====================================================================
@wrap_embedding_func_with_attrs(
    embedding_dim=3072,
    max_token_size=2048,
    model_name="models/gemini-embedding-001",
)
async def gemini_embedding_func(texts: list[str]) -> np.ndarray:
    """
    Uses Google Gemini's embedding-001 model via Langchain.
    Falls back to random vectors if GEMINI_API_KEY is missing (dev mode).
    """
    if not settings.GEMINI_API_KEY:
        # Dev fallback: random vectors so the system can still boot
        print("[LightRAG] WARNING: No GEMINI_API_KEY. Using random embeddings.")
        return np.random.rand(len(texts), 768).astype(np.float32)

    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    import asyncio
    
    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=settings.GEMINI_API_KEY,
    )
    
    # Process one by one to guarantee 1 vector per text
    vectors = []
    for text in texts:
        vec = await asyncio.to_thread(embeddings_model.embed_query, text)
        vectors.append(vec)
        
    return np.array(vectors, dtype=np.float32)


# =====================================================================
# 3. Singleton RAG instance (lazy-initialized)
# =====================================================================
_rag_instance: Optional[LightRAG] = None


async def get_rag() -> LightRAG:
    """Return a lazily-initialized, module-level LightRAG instance."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = LightRAG(
            working_dir=LIGHTRAG_WORKING_DIR,
            llm_model_func=groq_llm_complete,
            llm_model_name="llama-3.3-70b-versatile",
            embedding_func=gemini_embedding_func,
        )
        await _rag_instance.initialize_storages()
    return _rag_instance


# =====================================================================
# 4. Public API — drop-in replacements for the old graph_rag.py
# =====================================================================
async def build_graph_from_policies(file_path: str) -> None:
    """
    Reads a policy text file and ingests it into LightRAG.
    LightRAG automatically extracts entities, relations, and builds
    a local knowledge graph + vector index.
    """
    rag = await get_rag()

    with open(file_path, "r", encoding="utf-8") as f:
        policy_text = f.read()

    print(f"[LightRAG] Ingesting policies from {file_path} ...")
    await rag.ainsert(policy_text)
    print("[LightRAG] Policy ingestion complete.")


async def query_policy_graph(query: str, mode: str = "hybrid") -> str:
    """
    Queries the LightRAG knowledge graph.

    Modes:
        - "naive"  : pure vector search (like basic RAG)
        - "local"  : entity-centric graph traversal
        - "global" : broad thematic / community-level retrieval
        - "hybrid" : combines local + global (recommended default)
        - "mix"    : combines KG + vector retrieval
    """
    rag = await get_rag()

    result = await rag.aquery(
        query,
        param=QueryParam(mode=mode),
    )
    return result if result else "No matching policies found."


# =====================================================================
# 5. Synchronous wrappers (for the LangGraph nodes that call sync code)
# =====================================================================
def build_graph_from_policies_sync(file_path: str) -> None:
    """Synchronous wrapper for build_graph_from_policies."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pool.submit(asyncio.run, build_graph_from_policies(file_path)).result()
    else:
        asyncio.run(build_graph_from_policies(file_path))


def query_policy_graph_sync(query: str, mode: str = "hybrid") -> str:
    """Synchronous wrapper for query_policy_graph."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, query_policy_graph(query, mode))
            return future.result()
    else:
        return asyncio.run(query_policy_graph(query, mode))
