import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.tools.search_products import search_products
from app.tools.vendor_comparison import compare_vendors
from app.tools.budget_tools import check_budget, reserve_budget

def run_tests():
    print("--- 1. Testing search_products ---")
    # Search for laptops
    results = search_products.invoke({"query": "", "category": "Laptop"})
    print(results)
    
    print("\n--- 2. Testing vendor_comparison ---")
    # Extract the first ID from the results to test comparison
    first_id = None
    for line in results.split("\n"):
        if "- ID:" in line:
            first_id = line.split("|")[0].replace("- ID: ", "").strip()
            break
            
    if first_id:
        print(f"Comparing vendors for product ID: {first_id}")
        comparison = compare_vendors.invoke({"product_id": first_id})
        print(comparison)
    else:
        print("No product ID found to test.")
        
    print("\n--- 3. Testing budget_tools (Check Budget) ---")
    from app.database import SessionLocal
    from app.models import Department
    db = SessionLocal()
    first_dept = db.query(Department).first()
    dept_name = first_dept.name if first_dept else "Sales"
    db.close()
    
    budget_status = check_budget.invoke({"department_name": dept_name})
    print(budget_status)
    
    print("\n--- 4. Testing budget_tools (Reserve Budget - Optimistic Lock) ---")
    reserve_status = reserve_budget.invoke({"department_name": dept_name, "amount": 100.0})
    print(reserve_status)
    
    print("\n--- 5. Checking budget again to see version update ---")
    budget_status_after = check_budget.invoke({"department_name": dept_name})
    print(budget_status_after)

if __name__ == "__main__":
    run_tests()
