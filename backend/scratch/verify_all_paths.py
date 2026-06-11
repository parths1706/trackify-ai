import sys
sys.path.insert(0, '.')
import json
from dotenv import load_dotenv
load_dotenv()

from schemas.state import AgentState
from services.graph_service import intent_classifier

def test_classifier(question: str, history: list = []):
    print(f"\n--- Question: '{question}' ---")
    if history:
        print("History:")
        for m in history:
            print(f"  {m['role']}: {m['content']}")
            
    state: AgentState = {
        "user_question": question,
        "chat_history": history,
        "intent": None,
        "path": None,
        "raw_db_results": None,
        "final_response": None,
        "error_log": None,
        "retry_count": 0,
    }
    
    res = intent_classifier(state)
    print(f"Path Selected: {res.get('path')}")
    print("Intent JSON:", json.dumps(res.get("intent"), indent=2))

# 1. Simple
test_classifier("How many hours did Raj log this week?")

# 2. Memory
history_2 = [
    {"role": "user", "content": "What project is Sonu working on?"},
    {"role": "assistant", "content": "Sonu is working on the Web Redesign project."}
]
test_classifier("How many hours did he spend on that?", history_2)

# 3. Multi
test_classifier("Who are the most active employees and which projects are they on?")

# 4. Complex
test_classifier("Compare hours logged by all members of the Design team this month")

# 5. Greeting
test_classifier("Hey, what can you help me with?")
