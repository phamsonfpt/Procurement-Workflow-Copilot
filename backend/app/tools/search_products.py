from langchain_core.tools import tool
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models import Product

@tool
def search_products(query: str, category: str = None) -> str:
    """
    Search for products in the database by name or category.
    Use this tool when the user wants to find available products.
    """
    db: Session = SessionLocal()
    try:
        stmt = db.query(Product)
        if query:
            stmt = stmt.filter(Product.name.ilike(f"%{query}%"))
        if category:
            stmt = stmt.filter(Product.category.ilike(f"%{category}%"))
            
        products = stmt.limit(10).all()
        
        if not products:
            return "No products found matching the criteria."
            
        result = "Found products:\n"
        for p in products:
            result += f"- ID: {p.id} | Name: {p.name} | Category: {p.category}\n"
        return result
    finally:
        db.close()
