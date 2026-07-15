import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.orchestrator import build_orchestrator

def run_tests():
    print("--- Testing LangGraph Multi-Agent Orchestrator ---")
    
    app = build_orchestrator()
    
    initial_state = {
        "messages": [],
        "department_name": "Engineering",
        "product_query": "I want to buy a high-end Laptop for $2500"
    }
    
    print(f"Input State: {initial_state}")
    
    # Run the graph
    for output in app.stream(initial_state):
        # stream() yields dictionaries with node names as keys
        for key, value in output.items():
            print(f"\nOutput from node '{key}':")
            print("---")
            if "approval_status" in value:
                print(f"Status: {value['approval_status']}")
            if "final_report" in value:
                print(f"Report: {value['final_report']}")
            if "messages" in value:
                for m in value["messages"]:
                    print(f"Message: {m.content}")
            print("---\n")

if __name__ == "__main__":
    run_tests()
