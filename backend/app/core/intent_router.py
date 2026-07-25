import json
from enum import Enum
from langchain_groq import ChatGroq
from app.core.config import settings


class QueryIntent(str, Enum):
    SIMPLE_QA = "simple_qa"
    WORKFLOW_REASONING = "workflow_reasoning"


def _get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=settings.GROQ_API_KEY,
        timeout=15.0,
    )


async def classify_intent(query: str) -> QueryIntent:
    """
    Classifies a preprocessed query into SIMPLE_QA or WORKFLOW_REASONING
    using few-shot prompting.
    """
    llm = _get_llm()

    prompt = f"""You are an intent classifier for a Procurement Copilot.

Classify the following query into exactly one of two categories:

**SIMPLE_QA** — Factual, definitional, or lookup questions that can be answered from a single document section.
Examples:
- "What is a Purchase Order?"
- "What is the procurement policy?"
- "How do I create a Purchase Requisition?"
- "What are the payment terms?"
- "What is the approval threshold for Manager?"
- "Chính sách mua hàng là gì?"

**WORKFLOW_REASONING** — Questions that require connecting multiple entities, tracing relationships, or reasoning across multiple steps in a procurement workflow.
Examples:
- "Why hasn't my PR been converted to a PO?"
- "Which vendors supply electrical materials and what certifications do they need?"
- "What approvals are needed if Engineering wants to buy 10 Dell laptops worth $15,000?"
- "Can Marketing department buy a MacBook Pro?"
- "Is my $400 chair purchase considered budget splitting if I bought another $200 chair last week?"
- "Vendor A đã cung cấp những vật tư nào?"

Query: "{query}"

Respond with ONLY one word: SIMPLE_QA or WORKFLOW_REASONING"""

    try:
        response = await llm.ainvoke(prompt)
        answer = response.content.strip().upper()
        
        if "WORKFLOW" in answer:
            return QueryIntent.WORKFLOW_REASONING
        return QueryIntent.SIMPLE_QA
    except Exception:
        # Default to simple_qa on error (safer, faster)
        return QueryIntent.SIMPLE_QA
