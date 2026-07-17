from langchain_groq import ChatGroq
from config import GROQ_API_KEY, GROQ_MODEL_LARGE
from services.graph_service import run_graph
from tools import executors

client = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL_LARGE)
TOOLS = []

def build_api_messages(messages: list) -> list:
    return messages[-6:] if len(messages) > 6 else messages

def chat(messages: list, session_id: str = "default_thread") -> str:
    try:
        user_message = messages[-1]["content"] if messages else ""
        return run_graph(user_message, session_id=session_id)
    except Exception as e:
        return "I encountered an error. Please try again."

def execute_tool(name: str, args: dict) -> dict:
    from tools.definitions import TOOL_MAP
    fn = TOOL_MAP.get(name)
    if not fn:
        return {"error": f"Unknown tool: {name}"}
    try:
        return fn(**args)
    except Exception as e:
        return {"error": str(e)}
