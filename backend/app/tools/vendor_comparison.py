from langchain_core.tools import tool
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import SessionLocal
from app.models import VendorProduct, Vendor, Product

@tool
def compare_vendors(product_id: str, quantity: int = 1) -> str:
    """
    Compare prices and lead times from different vendors for a specific product ID.
    If quantity > 1, applies dynamic volume discounts from the vendor's contract.
    Use this tool to find the best deal for a given product and quantity.
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
            
        result = f"Vendor Comparison for {product.name} ({product.category}) - Quantity: {quantity}\n"
        for vp, vendor in offerings:
            base_unit_price = float(vp.price)
            discount_pct = 0.0
            
            # Calculate dynamic volume discount
            if vendor.discount_tiers and quantity > 1:
                # discount_tiers format e.g. {"10": 0.05, "50": 0.15}
                # Find the maximum tier that quantity satisfies
                applicable_tiers = [float(pct) for q, pct in vendor.discount_tiers.items() if quantity >= int(q)]
                if applicable_tiers:
                    discount_pct = max(applicable_tiers)
                    
            final_unit_price = base_unit_price * (1 - discount_pct)
            total_price = final_unit_price * quantity
            savings = (base_unit_price * quantity) - total_price
            
            result += f"- Vendor: {vendor.name} (Rating: {vendor.rating}/5.0)\n"
            result += f"  Base Unit Price: ${base_unit_price:,.2f}\n"
            if discount_pct > 0:
                result += f"  [VOLUME DISCOUNT APPLIED: {discount_pct*100:.0f}% off for ordering >= {quantity}]\n"
                result += f"  Final Unit Price: ${final_unit_price:,.2f}\n"
                result += f"  Total Savings: ${savings:,.2f}\n"
            result += f"  Total Cost: ${total_price:,.2f}\n"
            result += f"  Lead Time: {vp.lead_time_days} days\n\n"
            
        return result
    finally:
        db.close()
