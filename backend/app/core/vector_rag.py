import os
import asyncio
from typing import Optional
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal
from app.core.config import settings


# =====================================================================
# 1. Embedding function (Gemini API — no local model needed)
# =====================================================================
def _get_embeddings():
    """Google Gemini embedding-001 (cloud API, 768 dims, multilingual)."""
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=settings.GEMINI_API_KEY,
    )


# =====================================================================
# 2. Text Chunking
# =====================================================================
def chunk_text(
    text_content: str,
    source_file: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[dict]:
    """
    Splits text into overlapping chunks using a simple character-based
    approach with sentence-boundary awareness.
    """
    # Split by double newlines first (paragraph-level), then merge
    paragraphs = [p.strip() for p in text_content.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = ""
    chunk_index = 0

    for para in paragraphs:
        # If adding this paragraph exceeds chunk_size, save current and start new
        if len(current_chunk) + len(para) + 2 > chunk_size and current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "source_file": source_file,
                "chunk_index": chunk_index,
            })
            chunk_index += 1
            # Keep overlap from end of previous chunk
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + "\n\n" + para
            else:
                current_chunk = para
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append({
            "content": current_chunk.strip(),
            "source_file": source_file,
            "chunk_index": chunk_index,
        })

    return chunks


# =====================================================================
# 3. Ingestion — Chunk + Embed + Store in pgvector + tsvector
# =====================================================================
async def ingest_documents(file_path: str) -> int:
    """
    Reads a text file, chunks it, embeds each chunk using Gemini,
    and stores in the document_chunks table (pgvector + tsvector).

    Returns the number of chunks ingested.
    """
    source_file = os.path.basename(file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = chunk_text(content, source_file)
    if not chunks:
        print(f"[VectorRAG] No chunks generated from {file_path}")
        return 0

    print(f"[VectorRAG] Generated {len(chunks)} chunks from {source_file}")

    # Embed all chunks
    embeddings_model = _get_embeddings()
    texts = [c["content"] for c in chunks]

    print(f"[VectorRAG] Embedding {len(texts)} chunks via Gemini API...")
    vectors = await asyncio.to_thread(embeddings_model.embed_documents, texts)

    # Store in DB
    db: Session = SessionLocal()
    try:
        # Remove old chunks from same source file
        db.execute(
            text("DELETE FROM document_chunks WHERE source_file = :sf"),
            {"sf": source_file},
        )

        for chunk, vector in zip(chunks, vectors):
            vector_str = "[" + ",".join(str(v) for v in vector) + "]"
            db.execute(
                text("""
                    INSERT INTO document_chunks (content, source_file, chunk_index, embedding, created_at)
                    VALUES (:content, :source_file, :chunk_index, CAST(:embedding AS vector), NOW())
                """),
                {
                    "content": chunk["content"],
                    "source_file": chunk["source_file"],
                    "chunk_index": chunk["chunk_index"],
                    "embedding": vector_str,
                },
            )

        db.commit()
        print(f"[VectorRAG] Stored {len(chunks)} chunks in database.")
        return len(chunks)

    except Exception as e:
        db.rollback()
        print(f"[VectorRAG] Error storing chunks: {e}")
        raise
    finally:
        db.close()


async def ingest_directory(dir_path: str) -> int:
    """Ingest all .txt and .md files from a directory."""
    total = 0
    for filename in sorted(os.listdir(dir_path)):
        if filename.endswith((".txt", ".md")):
            filepath = os.path.join(dir_path, filename)
            count = await ingest_documents(filepath)
            total += count
    print(f"[VectorRAG] Total chunks ingested: {total}")
    return total


# =====================================================================
# 4. Hybrid Search — BM25 (tsvector) + Semantic (pgvector) + RRF
# =====================================================================
async def hybrid_search(
    query: str,
    top_k: int = 5,
    bm25_weight: float = 0.4,
    semantic_weight: float = 0.6,
) -> list[dict]:
    """
    Performs hybrid search combining:
    1. BM25 via PostgreSQL tsvector + ts_rank (lexical/keyword match)
    2. Semantic search via pgvector cosine similarity
    3. Reciprocal Rank Fusion (RRF) to merge results

    Returns list of {content, source_file, score} sorted by relevance.
    """
    # Embed the query
    embeddings_model = _get_embeddings()
    query_vector = await asyncio.to_thread(embeddings_model.embed_query, query)
    vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"

    db: Session = SessionLocal()
    try:
        # --- BM25 Search (PostgreSQL full-text search) ---
        bm25_sql = text("""
            SELECT id, content, source_file,
                   ts_rank(
                       to_tsvector('english', content),
                       plainto_tsquery('english', :query)
                   ) AS bm25_score
            FROM document_chunks
            WHERE to_tsvector('english', content) @@ plainto_tsquery('english', :query)
            ORDER BY bm25_score DESC
            LIMIT :limit
        """)
        bm25_results = db.execute(bm25_sql, {"query": query, "limit": top_k * 2}).fetchall()

        # --- Semantic Search (pgvector cosine similarity) ---
        semantic_sql = text(f"""
            SELECT id, content, source_file,
                   1 - (embedding <=> '{vector_str}') AS semantic_score
            FROM document_chunks
            ORDER BY embedding <=> '{vector_str}' ASC
            LIMIT :limit
        """)
        semantic_results = db.execute(semantic_sql, {"limit": top_k * 2}).fetchall()

        # --- Reciprocal Rank Fusion (RRF) ---
        k = 60  # RRF constant
        fused_scores: dict[int, dict] = {}

        for rank, row in enumerate(bm25_results):
            doc_id = row.id
            if doc_id not in fused_scores:
                fused_scores[doc_id] = {
                    "content": row.content,
                    "source_file": row.source_file,
                    "score": 0.0,
                }
            fused_scores[doc_id]["score"] += bm25_weight / (k + rank + 1)

        for rank, row in enumerate(semantic_results):
            doc_id = row.id
            if doc_id not in fused_scores:
                fused_scores[doc_id] = {
                    "content": row.content,
                    "source_file": row.source_file,
                    "score": 0.0,
                }
            fused_scores[doc_id]["score"] += semantic_weight / (k + rank + 1)

        # Sort by fused score
        results = sorted(fused_scores.values(), key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    except Exception as e:
        print(f"[VectorRAG] Hybrid search error: {e}")
        # Fallback to semantic-only search
        try:
            fallback_sql = text(f"""
                SELECT content, source_file,
                       1 - (embedding <=> '{vector_str}') AS score
                FROM document_chunks
                ORDER BY embedding <=> '{vector_str}' ASC
                LIMIT :limit
            """)
            results = db.execute(fallback_sql, {"limit": top_k}).fetchall()
            return [
                {"content": r.content, "source_file": r.source_file, "score": r.score}
                for r in results
            ]
        except Exception:
            return []
    finally:
        db.close()


# =====================================================================
# 5. Synchronous wrapper for LangGraph nodes
# =====================================================================
def hybrid_search_sync(query: str, top_k: int = 5) -> list[dict]:
    """Synchronous wrapper for hybrid_search."""
    import concurrent.futures

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, hybrid_search(query, top_k))
            return future.result()
    else:
        return asyncio.run(hybrid_search(query, top_k))
