"""
Unified Retrieval Engine — The brain that connects all retrieval components.

Architecture:
    User Query
        → Query Preprocessor (spell correct + rewrite)
        → Intent Router (classify: simple_qa / workflow_reasoning)
        → Route to:
            - simple_qa → Hybrid Vector RAG (BM25 + pgvector + RRF)
            - workflow_reasoning → LightRAG (Knowledge Graph)
        → LLM generates final answer with retrieved context
"""

import json
from langchain_groq import ChatGroq
from app.core.config import settings
from app.core.query_preprocessor import preprocess_query
from app.core.intent_router import classify_intent, QueryIntent
from app.core.vector_rag import hybrid_search
from app.core.light_rag import query_policy_graph


def _get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=settings.GROQ_API_KEY,
        timeout=30.0,
    )


async def retrieve_and_answer(raw_query: str) -> dict:
    """
    Full multi-tier retrieval pipeline:

    1. Preprocess → spell correct + expand abbreviations
    2. Intent Router → classify query type
    3. Route to appropriate retrieval system
    4. Generate LLM answer with retrieved context
    5. Return structured result

    Returns:
        {
            "answer": "...",
            "intent": "simple_qa" | "workflow_reasoning",
            "original_query": "...",
            "corrected_query": "...",
            "sources": [...],
            "retrieval_method": "hybrid_vector_rag" | "lightrag_knowledge_graph"
        }
    """
    # ── Step 1: Preprocess ──────────────────────────────────────────
    preprocessed = await preprocess_query(raw_query)
    corrected_query = preprocessed.get("corrected", raw_query)
    keywords = preprocessed.get("keywords", [])

    # ── Step 2: Intent Classification ───────────────────────────────
    intent = await classify_intent(corrected_query)

    # ── Step 3: Route to retrieval system ───────────────────────────
    context = ""
    sources = []
    retrieval_method = ""

    if intent == QueryIntent.SIMPLE_QA:
        # ── Path A: Hybrid Vector RAG ───────────────────────────────
        retrieval_method = "hybrid_vector_rag"
        search_results = await hybrid_search(corrected_query, top_k=5)

        if search_results:
            context_parts = []
            for i, result in enumerate(search_results, 1):
                context_parts.append(
                    f"[Source {i}: {result['source_file']}]\n{result['content']}"
                )
                sources.append({
                    "file": result["source_file"],
                    "score": round(result.get("score", 0), 4),
                })
            context = "\n\n---\n\n".join(context_parts)
        else:
            context = "No relevant documents found."

    else:
        # ── Path B: LightRAG (Knowledge Graph) ─────────────────────
        retrieval_method = "lightrag_knowledge_graph"

        # Use hybrid mode for best results (combines local + global graph traversal)
        context = await query_policy_graph(corrected_query, mode="hybrid")
        sources.append({"file": "knowledge_graph", "mode": "hybrid"})

    # ── Step 4: Generate LLM Answer ─────────────────────────────────
    llm = _get_llm()

    system_prompt = """You are a Procurement Copilot AI assistant for TechCorp Vietnam.
Your role is to help employees understand procurement policies, workflows, and procedures.

Rules:
- Answer based ONLY on the provided context. If the context doesn't contain the answer, say so.
- Be concise but thorough.
- If the question is in Vietnamese, answer in Vietnamese. If in English, answer in English.
- Reference specific policy sections when possible.
- Use bullet points for clarity."""

    user_prompt = f"""Context retrieved from company knowledge base:
---
{context}
---

User Question: {corrected_query}

Please answer the question based on the context above."""

    try:
        response = await llm.ainvoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        answer = response.content
    except Exception as e:
        answer = f"Error generating answer: {str(e)}"

    # ── Step 5: Return structured result ────────────────────────────
    return {
        "answer": answer,
        "intent": intent.value,
        "original_query": raw_query,
        "corrected_query": corrected_query,
        "keywords": keywords,
        "sources": sources,
        "retrieval_method": retrieval_method,
    }


async def retrieve_context_only(raw_query: str) -> str:
    """
    Lightweight version that only returns retrieved context (no LLM answer).
    Used by the LangGraph Policy Node to get policy context.
    """
    preprocessed = await preprocess_query(raw_query)
    corrected_query = preprocessed.get("corrected", raw_query)
    intent = await classify_intent(corrected_query)

    if intent == QueryIntent.SIMPLE_QA:
        results = await hybrid_search(corrected_query, top_k=5)
        if results:
            return "\n".join(
                f"- [{r['source_file']}] {r['content']}" for r in results
            )
        return "No matching policies found."
    else:
        return await query_policy_graph(corrected_query, mode="hybrid")


# =====================================================================
# Synchronous wrapper for LangGraph nodes
# =====================================================================
def retrieve_context_only_sync(raw_query: str) -> str:
    """Synchronous wrapper for retrieve_context_only."""
    import asyncio
    import concurrent.futures

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, retrieve_context_only(raw_query))
            return future.result()
    else:
        return asyncio.run(retrieve_context_only(raw_query))
