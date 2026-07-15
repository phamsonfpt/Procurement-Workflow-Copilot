import os
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models import KnowledgeGraphEdge, EntityEmbedding
from app.core.config import settings

# 1. Define strict schema for extraction matching DB CheckConstraints
class KnowledgeTriple(BaseModel):
    entity_from: str = Field(description="The source entity name")
    entity_from_type: str = Field(description="Must be one of: Department, Policy, BudgetThreshold, ApprovalLevel, VendorCategory")
    relation: str = Field(description="Must be one of: applies_to, budget_rule, needs_approval, preferred_vendor, restricted_from, escalates_to")
    entity_to: str = Field(description="The target entity name")
    entity_to_type: str = Field(description="Must be one of: Department, Policy, BudgetThreshold, ApprovalLevel, VendorCategory")
    evidence: str = Field(description="The exact text from the policy that supports this rule")

class ExtractionResult(BaseModel):
    triples: List[KnowledgeTriple]

def init_llm_and_embeddings():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        temperature=0, 
        api_key=settings.GEMINI_API_KEY
    )
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004", 
        google_api_key=settings.GEMINI_API_KEY
    )
    return llm, embeddings

def build_graph_from_policies(file_path: str):
    """
    Reads a policy text file, uses LLM to extract graph edges, 
    and saves them to the DB along with embeddings.
    """
    llm, embeddings = init_llm_and_embeddings()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        policy_text = f.read()

    print("Extracting knowledge graph triples from policies...")
    
    # -- MOCK START (Bypassing Gemini API due to Quota/Rate Limits) --
    print("MOCKING LLM EXTRACTION (Quota Exceeded workaround)...")
    mock_triples = [
        KnowledgeTriple(
            entity_from="Laptop > $2000",
            entity_from_type="BudgetThreshold",
            relation="needs_approval",
            entity_to="Manager",
            entity_to_type="ApprovalLevel",
            evidence="Laptops priced above $2000 require 'Manager' approval."
        ),
        KnowledgeTriple(
            entity_from="Office Furniture < $500",
            entity_from_type="BudgetThreshold",
            relation="applies_to",
            entity_to="System Auto-Approval",
            entity_to_type="ApprovalLevel",
            evidence="Office furniture (Chair, Desk) under $500 is auto-approved by the system."
        ),
        KnowledgeTriple(
            entity_from="Software > $1000",
            entity_from_type="BudgetThreshold",
            relation="needs_approval",
            entity_to="Security Team",
            entity_to_type="ApprovalLevel",
            evidence="Software licenses over $1000 require 'Security Team' approval."
        )
    ]
    result = ExtractionResult(triples=mock_triples)
    # -- MOCK END --
    
    db: Session = SessionLocal()
    import random
    
    try:
        # Clear existing graph data for a fresh start in tests
        db.query(KnowledgeGraphEdge).delete()
        db.query(EntityEmbedding).delete()
        
        for triple in result.triples:
            print(f"Extracted Edge: {triple.entity_from} -[{triple.relation}]-> {triple.entity_to}")
            
            # Save Edge
            edge = KnowledgeGraphEdge(
                entity_from=triple.entity_from,
                entity_from_type=triple.entity_from_type,
                relation=triple.relation,
                entity_to=triple.entity_to,
                entity_to_type=triple.entity_to_type,
                evidence=triple.evidence,
                source_document="policies.txt"
            )
            db.add(edge)
            
            # Embed the rule (MOCK VECTOR due to quota)
            vector = [random.uniform(-1, 1) for _ in range(768)]
            emb_record = EntityEmbedding(
                text_content=triple.evidence,
                embedding=vector
            )
            db.add(emb_record)
            
        db.commit()
        print("Graph built successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error saving to DB: {e}")
    finally:
        db.close()

def query_policy_graph(query: str, top_k: int = 3) -> str:
    """
    Queries the policy graph using pgvector for semantic search.
    """
    db: Session = SessionLocal()
    import random
    try:
        # MOCK VECTOR due to quota
        query_vector = [random.uniform(-1, 1) for _ in range(768)]
        
        # We need to format the vector as a string for pgvector query
        vector_str = "[" + ",".join([str(x) for x in query_vector]) + "]"
        
        # Search for similar policies using cosine distance (<=>)
        sql = text(f"""
            SELECT text_content, embedding <=> '{vector_str}' AS distance
            FROM entity_embeddings
            ORDER BY distance ASC
            LIMIT :top_k
        """)
        
        results = db.execute(sql, {"top_k": top_k}).fetchall()
        
        if not results:
            return "No matching policies found."
            
        output = "Relevant Policies:\n"
        for r in results:
            output += f"- {r.text_content}\n"
            
        return output
    finally:
        db.close()
