import asyncio
import httpx
import uuid
import sys

BASE_URL = "http://localhost:8000/api/chat"

async def test_scenario(name: str, query: str, user: dict, 
                        expected_interrupt: bool = False, 
                        expected_access_denied: bool = False,
                        expected_done: bool = False,
                        timeout: int = 120):
    print(f"\n--- Testing Scenario: {name} ---")
    thread_id = str(uuid.uuid4())
    payload = {
        "query": query,
        "department_name": user["department"],
        "thread_id": thread_id,
        "user_role": user["role"],
        "email": user["email"]
    }
    
    print(f"[{user['role']} - {user['department']}] Submitting request: '{query}'")
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", BASE_URL, json=payload, timeout=timeout) as response:
                interrupt_found = False
                access_denied_found = False
                done_found = False
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if '"type": "interrupt"' in data:
                            interrupt_found = True
                        elif '"type": "error"' in data and 'Access Denied' in data:
                            access_denied_found = True
                        elif '"type": "done"' in data:
                            done_found = True
                        elif '"type": "message"' in data:
                            print(f"  -> Agent msg: {data}")
                        elif '"type": "error"' in data:
                            print(f"  -> Agent err: {data}")
                            
                print(f"Result -> Interrupted: {interrupt_found}, Access Denied: {access_denied_found}, Done: {done_found}")
                
                if expected_access_denied:
                    assert access_denied_found, "Expected Access Denied but it was not found!"
                    print("✅ Scenario passed: Access was correctly denied.")
                    return thread_id

                if expected_interrupt:
                    assert interrupt_found, "Expected interruption for approval, but thread finished or failed!"
                    print("✅ Scenario passed: Request correctly requires approval (interrupted).")
                elif expected_done:
                    assert done_found, "Expected thread to finish automatically, but it didn't!"
                    print("✅ Scenario passed: Request finished automatically as expected.")
                    
                return thread_id
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return thread_id

async def test_approve(name: str, thread_id: str, approver: dict, expected_success: bool = True):
    print(f"\n--- Testing Scenario: {name} (Approving Thread {thread_id[:8]}...) ---")
    payload = {
        "query": "I approve this request.",
        "department_name": approver["department"],
        "thread_id": thread_id,
        "user_role": approver["role"],
        "email": approver["email"]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", BASE_URL, json=payload, timeout=60.0) as response:
                access_denied = False
                done_found = False
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if '"type": "error"' in data and 'Access Denied' in data:
                            access_denied = True
                        elif '"type": "done"' in data:
                            done_found = True
                            
                print(f"Result -> Access Denied: {access_denied}, Done: {done_found}")
                
                if expected_success:
                    assert done_found and not access_denied, "Expected successful approval but failed!"
                    print("✅ Scenario passed: Approval successful.")
                else:
                    assert access_denied, "Expected approval to fail due to RBAC but it succeeded!"
                    print("✅ Scenario passed: Approval correctly rejected due to RBAC.")
                    
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")

async def test_reject(name: str, thread_id: str, ops: dict):
    print(f"\n--- Testing Scenario: {name} (Rejecting Thread {thread_id[:8]}...) ---")
    payload = {
        "thread_id": thread_id,
        "email": ops["email"],
        "user_role": ops["role"]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BASE_URL}/reject", json=payload, timeout=60.0)
            data = response.json()
            if response.status_code == 200 and data.get("status") == "success":
                print("✅ Scenario passed: Request successfully rejected by Ops.")
            elif response.status_code == 403:
                print("✅ Scenario passed: Reject access denied (expected if not Ops).")
            else:
                print(f"❌ Test failed: Unexpected response {response.status_code} - {data}")
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")

async def main():
    # Users
    eng_emp = {"email": "emp1@acme.corp", "role": "Requester", "name": "Alice Nguyen", "department": "Engineering"}
    admin_emp = {"email": "admin1@acme.corp", "role": "Requester", "name": "Admin Staff", "department": "Admin"}
    manager = {"email": "manager_eng@acme.corp", "role": "Line Manager", "name": "Sarah Smith", "department": "Engineering"}
    head = {"email": "head_tech@acme.corp", "role": "Department Head", "name": "Mike Johnson", "department": "Engineering"}
    cfo = {"email": "cfo@acme.corp", "role": "CFO", "name": "Emily Davis", "department": "Executive"}
    ops = {"email": "ops@acme.corp", "role": "Ops", "name": "Ops Team", "department": "Admin"}

    print("========================================")
    print(" LEVEL 1: Basic Workflows (T1 - T4)")
    print("========================================")
    
    '''
    t1_id = await test_scenario("T1 - Auto Approve (<$1000)", "Buy a wireless mouse for $150", eng_emp, expected_done=True)
    t2_id = await test_scenario("T2 - Line Manager Routing ($2500)", "Buy a Dell Latitude Laptop for $2500", eng_emp, expected_interrupt=True)
    t3_id = await test_scenario("T3 - Dept Head Routing ($15000)", "Buy a Dell Server for $15000", eng_emp, expected_interrupt=True)
    t4_id = await test_scenario("T4 - CFO Routing ($60000)", "Buy new Dell Infrastructure for $60000", eng_emp, expected_interrupt=True)

    print("\n========================================")
    print(" LEVEL 2: RBAC & Security (T5 - T7)")
    print("========================================")
    
    await test_approve("T5 - Self Approval Attempt", t2_id, eng_emp, expected_success=False)
    await test_approve("T6 - Unauthorized Manager Approval", t3_id, manager, expected_success=False)
    await test_approve("T7 - Authorized Dept Head Approval", t3_id, head, expected_success=True)
    
    print("\n========================================")
    print(" LEVEL 3: Advanced AI Reasoning (T8 - T11)")
    print("========================================")
    
    # T8 - Over Budget (Trying to reserve 1,000,000 when dept budget is less)
    await test_scenario("T8 - Over Budget", "Buy 10000 Dell Laptops", eng_emp, expected_done=True)
    
    # T9 - Smurfing (Buying multiple small items)
    await test_scenario("T9.1 - Small Item 1", "Buy a Desk for $400", eng_emp, expected_done=True)
    await test_scenario("T9.2 - Small Item 2", "Buy a Chair for $400", eng_emp, expected_done=True)
    await test_scenario("T9.3 - Small Item 3 (Smurfing detection)", "Buy a Cabinet for $300", eng_emp, expected_interrupt=True)
    
    # T10 - Maverick Spend
    await test_scenario("T10 - Maverick Spend", "Buy an Apple MacBook Pro for $3000", eng_emp, expected_interrupt=True)
    '''
    
    # T11 - Role-based restriction
    await test_scenario("T11 - Engineering buys Gaming Laptop", "Buy a High-End Gaming Laptop for $2500", eng_emp, expected_interrupt=True)
    
    # T12 - Ops Reject
    '''
    print("\n========================================")
    print(" LEVEL 4: Ops Override (T12)")
    print("========================================")
    await test_reject("T12 - Ops Rejecting CFO pending thread", t4_id, ops)
    '''
    
if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
