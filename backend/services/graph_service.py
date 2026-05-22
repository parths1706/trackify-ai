from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from schemas.state import AgentState
from config import GROQ_API_KEY
from database import db
from datetime import datetime, timezone
from tools import executors
import json

# Model 1 — intent picker (llama 4, smarter)
llm_picker = ChatGroq(
    api_key=GROQ_API_KEY,
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0
)

# Model 2 — answer formatter (small, fast, cheap)
llm_formatter = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama-3.1-8b-instant",
    temperature=0
)

EXECUTOR_MAP = {
    "get_user_hours": executors.get_user_hours,
    "get_user_projects": executors.get_user_projects,
    "get_project_contributors": executors.get_project_contributors,
    "get_active_employees": executors.get_active_employees,
    "get_project_stats": executors.get_project_stats,
    "get_general_count": executors.get_general_count,
    "get_user_recent_activity": executors.get_user_recent_activity,
    "get_idle_employees": executors.get_idle_employees,
}

system_prompt_template = """You are an intent classifier for a time-tracking analytics chatbot.
Your only job is to read the user question and output a JSON object selecting which function to call.

AVAILABLE FUNCTIONS:
1. get_user_hours — use when asked about hours a person worked. Params: user_name(required), start_date(optional YYYY-MM-DD), end_date(optional YYYY-MM-DD)
2. get_user_projects — use when asked which projects a person is assigned to or working on. Params: user_name(required), include_archived(optional bool default false)
3. get_project_contributors — use when asked who worked on a project or top contributors. Params: project_name(required), start_date(optional), end_date(optional), limit(optional int default 10)
4. get_active_employees — use when asked who worked most, top employees by hours, most active people. Params: start_date(optional), end_date(optional), limit(optional int default 10)
5. get_project_stats — use when asked for project summary, total hours on a project, project details. Params: project_name(required), start_date(optional), end_date(optional)
6. get_general_count — use when asked how many users, projects, tasks, or teams exist. Params: entity(required — one of: users, projects, tasks, teams)
7. get_user_recent_activity — use when asked what someone is currently working on, their latest project, most recent work. Params: user_name(required)
8. get_idle_employees — use when asked who has not logged hours, inactive employees, who is idle. Params: days(optional int default 7)

DATE RULES:
- "this week" = Monday of current week to today
- "last week" = Monday to Sunday of previous week  
- "this month" = first day of current month to today
- "last month" = full previous month
- "today" = today only
- Always output dates as YYYY-MM-DD strings
- Today's date is: {today}

OUTPUT FORMAT — only valid JSON, no explanation, no markdown:
{
  "function": "function_name_here",
  "params": {
    "param1": "value1"
  }
}

If the question is a greeting or cannot be answered with data (example: "hello", "what can you do"), output:
{
  "function": "direct_answer",
  "params": {},
  "answer": "your friendly response here"
}"""

def pick_function(state: AgentState) -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    system = system_prompt_template.replace("{today}", today)
    
    # Build conversation history context
    history = state.get("chat_history", [])
    recent_history = history[-6:] if len(history) > 6 else history
    
    history_text = ""
    if recent_history:
        history_lines = []
        for msg in recent_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                history_lines.append(f"User: {content}")
            elif role == "assistant":
                history_lines.append(f"Assistant: {content}")
        if history_lines:
            history_text = "\n\nPREVIOUS CONVERSATION:\n" + "\n".join(history_lines) + "\n\nUse this context to resolve pronouns like 'him', 'her', 'his', 'same person', 'same project', 'what about them' etc."
    
    full_system = system + history_text
    
    messages = [
        SystemMessage(content=full_system),
        HumanMessage(content=state["user_question"])
    ]
    
    try:
        response = llm_picker.invoke(messages)
        content = response.content.strip()
        # Strip markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        parsed = json.loads(content.strip())
        return {
            "generated_pipeline": parsed,
            "error_log": None
        }
    except Exception as e:
        return {
            "generated_pipeline": {"function": "direct_answer", "params": {}, "answer": "I had trouble understanding that question. Could you rephrase it?"},
            "error_log": str(e)
        }

def execute_function(state: AgentState) -> dict:
    parsed = state.get("generated_pipeline", {})
    
    function_name = parsed.get("function")
    params = parsed.get("params", {})
    
    # Handle direct answers (greetings etc)
    if function_name == "direct_answer":
        return {
            "raw_db_results": {"direct_answer": parsed.get("answer", "Hello! Ask me anything about your team.")}
        }
    
    # Look up executor
    executor_fn = EXECUTOR_MAP.get(function_name)
    if not executor_fn:
        return {
            "raw_db_results": {"error": f"Unknown function: {function_name}"}
        }
    
    try:
        # Clean params — remove None values
        clean_params = {k: v for k, v in params.items() if v is not None and v != ""}
        result = executor_fn(**clean_params)
        return {"raw_db_results": result, "error_log": None}
    except Exception as e:
        return {
            "raw_db_results": {"error": f"Execution failed: {str(e)}"},
            "error_log": str(e)
        }

def format_answer(state: AgentState) -> dict:
    raw = state.get("raw_db_results", {})
    question = state["user_question"]
    
    # Handle direct answers without calling LLM
    if isinstance(raw, dict) and "direct_answer" in raw:
        return {"final_response": raw["direct_answer"]}
    
    # Handle errors
    if isinstance(raw, dict) and "error" in raw:
        return {"final_response": f"I could not find that information. {raw['error']}"}
    
    # Truncate large results to avoid token limits
    raw_str = json.dumps(raw, default=str)
    if len(raw_str) > 2000:
        raw_str = raw_str[:2000] + "... results truncated"
    
    messages = [
        SystemMessage(content="""You are Trackify AI, a friendly assistant for a company time-tracking platform.
Convert the database result into a clear plain English response.
Rules:
- Never use markdown, asterisks, bold, or bullet points
- Write in plain conversational sentences only
- Duration values are in hours already, just say X hours
- Do not mention database terms, JSON, or technical words
- Be concise and natural
- If the data shows a list, mention the top items naturally in a sentence"""),
        HumanMessage(content=f"User asked: {question}\n\nData: {raw_str}")
    ]
    
    try:
        response = llm_formatter.invoke(messages)
        return {"final_response": response.content.strip()}
    except Exception as e:
        # If formatter fails due to token limit, do simple formatting
        return {"final_response": f"Here is what I found: {raw_str[:500]}"}

workflow = StateGraph(AgentState)
workflow.add_node("pick_function", pick_function)
workflow.add_node("execute_function", execute_function)
workflow.add_node("format_answer", format_answer)

workflow.set_entry_point("pick_function")
workflow.add_edge("pick_function", "execute_function")
workflow.add_edge("execute_function", "format_answer")
workflow.add_edge("format_answer", END)

graph = workflow.compile()

def run_graph(user_question: str, chat_history: list = None) -> str:
    initial_state = AgentState(
        user_question=user_question,
        chat_history=chat_history or [],
        generated_pipeline=None,
        target_collection=None,
        raw_db_results=None,
        final_response=None,
        error_log=None,
        retry_count=0
    )
    result = graph.invoke(initial_state)
    return result.get("final_response", "I could not process your request.")
