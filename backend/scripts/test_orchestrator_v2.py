import asyncio
import uuid
import sys
import os

# Add parent dir to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.orchestrator import build_orchestrator
from app.core.checkpointer import get_checkpointer

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # Fix console encoding for Vietnamese characters
    sys.stdout.reconfigure(encoding='utf-8')

async def main():
    print("--- Testing LangGraph 6-Agent Orchestrator with Postgres Checkpointer ---")
    
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    print(f"Generated Thread ID: {thread_id}")
    
    initial_state = {
        "messages": [],
        "department_name": "Engineering",
        "product_query": "I want to buy a high-end Laptop for $2500"
    }
    
    async with get_checkpointer() as checkpointer:
        app = build_orchestrator(checkpointer)
        
        print("\n[STARTING GRAPH]")
        # Lần 1: Chạy từ đầu, nó sẽ đi qua 5 node và DỪNG ở human_review
        async for output in app.astream(initial_state, config=config, stream_mode="updates"):
            for node_name, state_changes in output.items():
                print(f"\n[NODE COMPLETED]: {node_name}")
                if "messages" in state_changes and len(state_changes["messages"]) > 0:
                    print(f"Message: {state_changes['messages'][-1].content}")
        
        # Kiểm tra xem nó có đang bị ngắt không
        final_state = await app.aget_state(config)
        if final_state.next:
            print(f"\n[INTERRUPT DETECTED] Workflow is paused at node(s): {final_state.next}")
        else:
            print("\n[WORKFLOW ENDED]")
            
        print("\n--- Test Completed Successfully ---")

if __name__ == "__main__":
    asyncio.run(main())
