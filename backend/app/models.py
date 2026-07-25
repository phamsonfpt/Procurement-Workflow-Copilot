import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Text, Numeric, Integer, ForeignKey, DateTime, CheckConstraint, JSON
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class Department(Base):
    __tablename__ = 'departments'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    users = relationship("User", back_populates="department")
    budget = relationship("Budget", back_populates="department", uselist=False)

class User(Base):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey('departments.id'))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    department = relationship("Department", back_populates="users")
    requests = relationship("PurchaseRequest", foreign_keys="PurchaseRequest.requester_id", back_populates="requester")

class Budget(Base):
    __tablename__ = 'budgets'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('departments.id'), unique=True, nullable=False)
    total_budget: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    used_budget: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # [FIX-1] Optimistic Locking version column
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __mapper_args__ = {
        "version_id_col": version
    }

    department = relationship("Department", back_populates="budget")

class PurchaseRequest(Base):
    __tablename__ = 'purchase_requests'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requester_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text)
    total_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    approval_level: Mapped[Optional[str]] = mapped_column(String(100))
    ai_recommendation: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # [FIX-2] Reconnect & state recovery
    langgraph_thread_id: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    requester = relationship("User", back_populates="requests")
    items = relationship("RequestItem", back_populates="purchase_request")
    approvals = relationship("Approval", back_populates="purchase_request")

class Product(Base):
    __tablename__ = 'products'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    specifications: Mapped[dict] = mapped_column(JSONB)
    description: Mapped[str] = mapped_column(Text)

    vendor_products = relationship("VendorProduct", back_populates="product")

class Vendor(Base):
    __tablename__ = 'vendors'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rating: Mapped[float] = mapped_column(Numeric(3, 2))
    contact_email: Mapped[str] = mapped_column(String(255))
    warranty_months: Mapped[int] = mapped_column(Integer, default=12)
    
    # [FEATURE] Dynamic discount tiers for volume discount logic
    # Example: {"10": 0.10, "50": 0.20} -> 10% off for >= 10 units
    discount_tiers: Mapped[Optional[dict]] = mapped_column(JSONB)

    vendor_products = relationship("VendorProduct", back_populates="vendor")

class VendorProduct(Base):
    __tablename__ = 'vendor_products'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('vendors.id'), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('products.id'), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer)

    vendor = relationship("Vendor", back_populates="vendor_products")
    product = relationship("Product", back_populates="vendor_products")

class RequestItem(Base):
    __tablename__ = 'request_items'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('purchase_requests.id'), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('products.id'), nullable=False)
    vendor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('vendors.id'), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)

    purchase_request = relationship("PurchaseRequest", back_populates="items")
    product = relationship("Product")
    vendor = relationship("Vendor")

class Approval(Base):
    __tablename__ = 'approvals'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('purchase_requests.id'), nullable=False)
    approver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    decision: Mapped[Optional[str]] = mapped_column(String(50)) # e.g. "approved", "rejected", "pending"
    comment: Mapped[Optional[str]] = mapped_column(Text)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    purchase_request = relationship("PurchaseRequest", back_populates="approvals")
    approver = relationship("User")

# GraphRAG Schema
class KnowledgeGraphEdge(Base):
    __tablename__ = 'knowledge_graph_edges'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_from: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # [FIX-4] DB-level type enforcement
    entity_from_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # [FIX-4] DB-level relation enforcement
    relation: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    entity_to: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_to_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    source_document: Mapped[Optional[str]] = mapped_column(String(255))
    evidence: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("entity_from_type IN ('Department', 'Policy', 'BudgetThreshold', 'ApprovalLevel', 'VendorCategory')"),
        CheckConstraint("entity_to_type IN ('Department', 'Policy', 'BudgetThreshold', 'ApprovalLevel', 'VendorCategory')"),
        CheckConstraint("relation IN ('applies_to', 'budget_rule', 'needs_approval', 'preferred_vendor', 'restricted_from', 'escalates_to')"),
    )

class EntityEmbedding(Base):
    __tablename__ = 'entity_embeddings'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(768)) # Default Gemini embedding dimension
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)


# =====================================================================
# Hybrid Vector RAG Schema (BM25 + pgvector)
# =====================================================================
class DocumentChunk(Base):
    """
    Stores chunked policy documents for Hybrid Vector RAG.
    - `embedding`: pgvector column for semantic search
    - `content`: used with PostgreSQL tsvector for BM25 full-text search
    """
    __tablename__ = 'document_chunks'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_file: Mapped[Optional[str]] = mapped_column(String(255))
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    embedding = mapped_column(Vector(3072))  # Gemini text-embedding-004 dimension
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
