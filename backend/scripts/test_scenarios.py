import asyncio
import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.orchestrator import build_orchestrator
from app.database import SessionLocal
from app.models import User, Department

async def run_scenario(name: str, query: str, user_email: str):
    print(f"\n{'='*50}")
    print(f"🚀 SCENARIO: {name}")
    print(f"👤 USER: {user_email}")
    print(f"📝 QUERY: '{query}'")
    print(f"{'='*50}\n")
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            print(f"❌ User {user_email} not found in DB. Make sure you ran generate_seed.py!")
            return
            
        dept = db.query(Department).filter(Department.id == user.department_id).first()
        dept_name = dept.name if dept else "Unknown"
        dept_id = str(dept.id) if dept else ""
        req_id = str(user.id)
        
    finally:
        db.close()
        
    # Build Graph
    graph = build_orchestrator()
    
    # Initial State
    initial_state = {
        "messages": [],
        "product_query": query,
        "department_name": dept_name,
        "department_id": dept_id,
        "requester_id": req_id
    }
    
    # Run Graph
    config = {"configurable": {"thread_id": f"test_{name.replace(' ', '_')}"}}
    print("⏳ Executing AI Copilot...\n")
    
    try:
        async for output in graph.astream(initial_state, config=config):
            for node_name, state_update in output.items():
                print(f"--- [FINISHED NODE: {node_name}] ---")
                if "messages" in state_update and state_update["messages"]:
                    print(f"🤖 AI Output: {state_update['messages'][-1].content}\n")
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        
    print(f"{'='*50}\n")

async def main():
    db = SessionLocal()
    try:
        eng_user = db.query(User).join(Department).filter(Department.code == "ENG").first()
        hr_user = db.query(User).join(Department).filter(Department.code == "HR").first()
        sales_user = db.query(User).join(Department).filter(Department.code == "SALES").first()
        
        eng_email = eng_user.email if eng_user else "eng@example.com"
        hr_email = hr_user.email if hr_user else "hr@example.com"
        sales_email = sales_user.email if sales_user else "sales@example.com"
    finally:
        db.close()
        
    # Scenario 1: Duplicate Order (Same Dept)
    await run_scenario(
        "Duplicate Order Warning",
        "Tôi cần mua thêm 20 máy tính xách tay (Laptop) cho phòng",
        eng_email
    )
    
    # Scenario 2: Demand Aggregation (Different Dept)
    await run_scenario(
        "Demand Aggregation (Volume Discount)",
        "Xin chào, phòng tôi cần 5 cái laptop mới.",
        hr_email
    )
    
    # Scenario 3: Role-based Violation
    await run_scenario(
        "Role-Based Policy Violation",
        "Tôi cần mua 1 cái Macbook Pro cấu hình cao nhất để làm việc.",
        hr_email
    )
    
    # Scenario 4: Maverick Spend (Contract Violation)
    await run_scenario(
        "Maverick Spend (Preferred Vendor Violation)",
        "Mua cho tôi 5 cái máy tính Apple iMac.",
        eng_email
    )
    
    # Scenario 5: Budget Splitting (Smurfing)
    await run_scenario(
        "Budget Splitting (Smurfing) Detection",
        "Tôi muốn xin mua 1 cái ghế văn phòng (Chair) giá khoảng 400 đô la.",
        eng_email
    )

if __name__ == "__main__":
    asyncio.run(main())
