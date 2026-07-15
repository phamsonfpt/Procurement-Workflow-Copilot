from langchain_core.tools import tool
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import SessionLocal
from app.models import VendorProduct, Vendor, Product

@tool
def compare_vendors(product_id: str) -> str:
    """
    Compare prices and lead times from different vendors for a specific product ID.
    Use this tool to find the best deal for a given product.
    """
    db: Session = SessionLocal()
    try:
        # Check if product exists
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return f"Product with ID {product_id} not found."
            
        # Get vendor offerings
        offerings = db.query(VendorProduct, Vendor).join(Vendor).filter(VendorProduct.product_id == product_id).all()
        
        if not offerings:
            return f"No vendors found selling {product.name}."
            
        result = f"Vendor Comparison for {product.name} ({product.category}):\n"
        for vp, vendor in offerings:
            result += f"- Vendor: {vendor.name} (Rating: {vendor.rating}/10)\n"
            result += f"  Price: ${vp.price}\n"
            result += f"  Lead Time: {vp.lead_time_days} days\n\n"
            
        return result
    finally:
        db.close()
