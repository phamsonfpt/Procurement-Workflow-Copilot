from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

def get_llm():
    return ChatGoogleGenerativeAI(
        model=settings.DEFAULT_LLM_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.0
    )
