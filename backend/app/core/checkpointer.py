import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.config import settings

from psycopg_pool import AsyncConnectionPool

# Lấy connection string từ config (dùng cổng 6543 nguyên bản của Supabase transaction mode)
DATABASE_URL = settings.DATABASE_URL
pool_url = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")

# Global connection pool instance
_pool: AsyncConnectionPool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=pool_url,
            max_size=10,
            kwargs={"autocommit": True, "prepare_threshold": None}
        )
    return _pool

@asynccontextmanager
async def get_checkpointer() -> AsyncGenerator[AsyncPostgresSaver, None]:
    """
    Context manager to yield a LangGraph Postgres Checkpointer.
    """
    pool = get_pool()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    yield checkpointer

async def close_pool():
    # Không cần close thủ công vì context manager đã lo
    pass
