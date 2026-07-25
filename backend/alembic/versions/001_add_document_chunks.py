"""add document_chunks table for hybrid vector rag

Revision ID: 001_add_document_chunks
Revises: 
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers
revision = '001_add_document_chunks'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source_file', sa.String(255)),
        sa.Column('chunk_index', sa.Integer(), default=0),
        sa.Column('embedding', Vector(3072)),
        sa.Column('metadata', sa.JSON()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # Index for BM25 full-text search (GIN on tsvector)
    op.execute("""
        CREATE INDEX idx_doc_chunks_ts 
        ON document_chunks 
        USING GIN(to_tsvector('english', content))
    """)

    # Index for vector similarity search (HNSW)
    op.execute("""
        CREATE INDEX idx_doc_chunks_embedding 
        ON document_chunks 
        USING hnsw(embedding vector_cosine_ops)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_doc_chunks_embedding")
    op.execute("DROP INDEX IF EXISTS idx_doc_chunks_ts")
    op.drop_table('document_chunks')
