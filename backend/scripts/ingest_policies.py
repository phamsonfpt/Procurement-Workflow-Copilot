"""
Ingestion Script — Loads policy documents into BOTH retrieval systems:
  1. Hybrid Vector RAG (chunk + embed + pgvector/tsvector)
  2. LightRAG (entity extraction + knowledge graph)

Usage:
    cd backend
    uv run python scripts/ingest_policies.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.stdout.reconfigure(encoding="utf-8")

from app.core.vector_rag import ingest_directory
from app.core.light_rag import build_graph_from_policies


async def main():
    policies_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "data", "policies"
    )

    if not os.path.isdir(policies_dir):
        print(f"ERROR: Policies directory not found: {policies_dir}")
        return

    files = [f for f in os.listdir(policies_dir) if f.endswith((".txt", ".md"))]
    print(f"Found {len(files)} policy documents in {policies_dir}")
    print("=" * 60)

    # ── Step 1: Ingest into Hybrid Vector RAG ───────────────────
    print("\n📄 [STEP 1/2] Ingesting into Hybrid Vector RAG (pgvector + tsvector)...")
    try:
        total_chunks = await ingest_directory(policies_dir)
        print(f"✅ Vector RAG: {total_chunks} chunks stored in database.\n")
    except Exception as e:
        print(f"❌ Vector RAG ingestion failed: {e}\n")

    # ── Step 2: Ingest into LightRAG Knowledge Graph ────────────
    print("🔗 [STEP 2/2] Ingesting into LightRAG Knowledge Graph...")
    try:
        for filename in files:
            filepath = os.path.join(policies_dir, filename)
            print(f"  Processing: {filename}")
            await build_graph_from_policies(filepath)
        print("✅ LightRAG: Knowledge graph built successfully.\n")
    except Exception as e:
        print(f"❌ LightRAG ingestion failed: {e}\n")

    print("=" * 60)
    print("🎉 Ingestion complete! Both retrieval systems are ready.")
    print("   - Vector RAG: BM25 + Semantic search via pgvector")
    print("   - LightRAG:   Knowledge Graph for multi-hop reasoning")


if __name__ == "__main__":
    asyncio.run(main())
