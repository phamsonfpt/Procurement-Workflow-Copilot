import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.graph_rag import build_graph_from_policies, query_policy_graph

def run_tests():
    print("--- 1. Building Knowledge Graph from Policies ---")
    policy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "policies.txt")
    build_graph_from_policies(policy_path)
    
    print("\n--- 2. Querying GraphRAG ---")
    # Test queries
    queries = [
        "What is the approval rule for a $2500 Laptop?",
        "Who approves software licenses over $1500?",
        "What happens if I buy a $300 chair?"
    ]
    
    for q in queries:
        print(f"\nQ: {q}")
        print(query_policy_graph(q))

if __name__ == "__main__":
    run_tests()
