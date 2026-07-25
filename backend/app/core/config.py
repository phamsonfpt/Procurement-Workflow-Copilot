import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Procurement Workflow Copilot"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # LLM Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    DEFAULT_LLM_MODEL: str = "gemini-2.0-flash"

    # Supabase Settings (if needed for storage, etc.)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # LightRAG Settings
    LIGHTRAG_WORKING_DIR: str = os.getenv("LIGHTRAG_WORKING_DIR", "./lightrag_data")
    
    class Config:
        env_file = ".env"

settings = Settings()
