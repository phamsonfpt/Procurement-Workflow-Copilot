import json
from langchain_groq import ChatGroq
from app.core.config import settings


def _get_llm():
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=settings.GROQ_API_KEY,
        timeout=15.0,
    )


async def preprocess_query(raw_query: str) -> dict:
    """
    Preprocesses a raw user query:
    1. Corrects spelling errors (Vietnamese & English)
    2. Expands abbreviations (PR, PO, GRN, RFQ...)
    3. Detects language
    4. Extracts search keywords

    Returns:
        {
            "original": "tao po",
            "corrected": "Tạo Purchase Order",
            "keywords": ["purchase order", "create"],
            "language": "vi"
        }
    """
    llm = _get_llm()

    prompt = f"""You are a query preprocessor for a Procurement Copilot system.

Given the user query below, perform these tasks:
1. SPELL CORRECTION: Fix any typos or misspellings in Vietnamese or English.
2. ABBREVIATION EXPANSION: Expand procurement abbreviations:
   - PR = Purchase Requisition
   - PO = Purchase Order  
   - GRN = Goods Receipt Note
   - RFQ = Request for Quotation
   - SOW = Statement of Work
   - SLA = Service Level Agreement
   - NDA = Non-Disclosure Agreement
   - BOM = Bill of Materials
   - AP = Accounts Payable
   - AR = Accounts Receivable
3. LANGUAGE: Detect if the query is in "vi" (Vietnamese) or "en" (English) or "mixed".
4. KEYWORDS: Extract 2-5 key search terms relevant to procurement.

User Query: "{raw_query}"

Respond in STRICT JSON format only, no explanation:
{{{{
  "corrected": "<corrected query>",
  "keywords": ["keyword1", "keyword2"],
  "language": "vi" or "en" or "mixed"
}}}}"""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        
        # Try to extract JSON from the response
        # Handle cases where LLM wraps in ```json ... ```
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        result = json.loads(content)
        result["original"] = raw_query
        return result
    except Exception as e:
        # Fallback: return original query if preprocessing fails
        return {
            "original": raw_query,
            "corrected": raw_query,
            "keywords": raw_query.lower().split()[:5],
            "language": "unknown",
            "error": str(e),
        }
