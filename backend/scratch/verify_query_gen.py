import sys
sys.path.insert(0, '.')
import json
from dotenv import load_dotenv
load_dotenv()

from schemas.state import AgentState
from services.graph_service import execute_query_gen

state: AgentState = {
    "user_question": "Compare hours logged by all members of the Design team this month",
    "chat_history": [],
    "intent": {"path": "query_gen", "intent": "Compare hours logged by all members of the Design team this month"},
    "path": "query_gen",
    "raw_db_results": None,
    "final_response": None,
    "error_log": None,
    "retry_count": 0,
}

print("Running execute_query_gen...")
res_state = execute_query_gen(state)
print("\nraw_db_results:")
print(json.dumps(res_state.get("raw_db_results"), indent=2))
