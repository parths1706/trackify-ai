import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.graph_service import run_graph

def test_flow():
    # Interaction 1
    q1 = "last month average hours logged by the team?"
    chat_history = []
    print(f"User: {q1}")
    a1 = run_graph(q1, chat_history)
    print(f"Assistant: {a1}")

    # Interaction 2
    q2 = "should be 8"
    chat_history.append({"role": "user", "content": q1})
    chat_history.append({"role": "assistant", "content": a1})
    print(f"User: {q2}")
    a2 = run_graph(q2, chat_history)
    print(f"Assistant: {a2}")

if __name__ == "__main__":
    test_flow()
