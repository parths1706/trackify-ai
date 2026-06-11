import json
import re
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langsmith import traceable
from schemas.state import AgentState
from tools.executors import (
    get_user_hours, get_user_projects, get_project_contributors,
    get_active_employees, get_project_stats, get_general_count,
    get_user_recent_activity, get_idle_employees, validate_pipeline
)
from config import GROQ_API_KEY, GROQ_MODEL_LARGE, GROQ_MODEL_SMALL, GEMINI_API_KEY, GEMINI_MODEL
from database import db
import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)

# ── LLM clients ──────────────────────────────────────────────────────────────
llm_classifier = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL_LARGE, temperature=0)
llm_formatter   = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL_SMALL, temperature=0)

# ── Executor map ─────────────────────────────────────────────────────────────
EXECUTOR_MAP = {
    "get_user_hours":           get_user_hours,
    "get_user_projects":        get_user_projects,
    "get_project_contributors": get_project_contributors,
    "get_active_employees":     get_active_employees,
    "get_project_stats":        get_project_stats,
    "get_general_count":        get_general_count,
    "get_user_recent_activity": get_user_recent_activity,
    "get_idle_employees":       get_idle_employees,
}

# ── History helper ────────────────────────────────────────────────────────────
def build_history_text(chat_history: list, limit: int = 10) -> str:
    if not chat_history:
        return "No previous conversation."
    lines = []
    for msg in chat_history[-limit:]:
        role = "Manager" if msg.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {msg.get('content', '')}")
    return "\n".join(lines)

# ── NODE 1: intent_classifier ─────────────────────────────────────────────────
def intent_classifier(state: AgentState) -> AgentState:
    history_text = build_history_text(state["chat_history"], limit=10)
    
    system_prompt = f"""You are an intent classifier for a time tracking analytics system.

CONVERSATION HISTORY (resolve all pronouns and references using this):
{history_text}

AVAILABLE EXECUTOR FUNCTIONS:
- get_user_hours(user_name, start_date, end_date) — total hours a person logged
- get_user_projects(user_name, include_archived) — projects a person works on
- get_project_contributors(project_name, start_date, end_date, limit) — who worked on a project
- get_active_employees(start_date, end_date, limit) — employees ranked by hours
- get_project_stats(project_name, start_date, end_date) — project summary
- get_general_count(entity) — count of users/projects/tasks/teams
- get_user_recent_activity(user_name) — most recent project a person worked on
- get_idle_employees(days) — employees with no hours in last N days

INSTRUCTIONS:
1. Use conversation history to resolve pronouns (he/she/him/they/same/that/it)
   Example: if history shows discussion about "Raj" and user asks "what about him" → resolve to "Raj"
2. Use today's date context for relative dates (this week, last month, yesterday)
3. Choose ONE of three output paths:

PATH A — single known executor fits the question:
{{"path": "executor", "function": "function_name", "params": {{...}}}}

PATH B — question needs 2-3 executor calls combined:
{{"path": "multi", "steps": [{{"function": "...", "params": {{...}}}}, {{"function": "...", "params": {{...}}}}]}}

PATH C — question is too complex or does not match any executor:
{{"path": "query_gen", "intent": "plain English description of exactly what data is needed"}}

PATH D — greeting or non-data question:
{{"path": "direct", "answer": "your response here"}}

Return ONLY valid JSON. No explanation. No markdown."""

    response = llm_classifier.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["user_question"]}
    ])
    
    try:
        text = response.content.strip()
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            text = text[start_idx:end_idx + 1]
        intent = json.loads(text)
    except Exception as e:
        intent = {"path": "query_gen", "intent": state["user_question"]}
    
    return {**state, "intent": intent, "path": intent.get("path", "query_gen")}


# ── NODE 2a: execute_known ────────────────────────────────────────────────────
def execute_known(state: AgentState) -> AgentState:
    intent = state["intent"]
    func_name = intent.get("function", "")
    params = intent.get("params", {})
    
    executor = EXECUTOR_MAP.get(func_name)
    if not executor:
        return {**state, "raw_db_results": {"error": f"Unknown function: {func_name}"}}
    
    try:
        result = executor(**{k: v for k, v in params.items() if v is not None})
        return {**state, "raw_db_results": result}
    except Exception as e:
        return {**state, "raw_db_results": {"error": str(e)}}


# ── NODE 2b: execute_multi ────────────────────────────────────────────────────
def execute_multi(state: AgentState) -> AgentState:
    steps = state["intent"].get("steps", [])
    combined = {}
    
    for i, step in enumerate(steps):
        func_name = step.get("function", "")
        params = step.get("params", {})
        executor = EXECUTOR_MAP.get(func_name)
        if executor:
            try:
                result = executor(**{k: v for k, v in params.items() if v is not None})
                combined[f"result_{i+1}_{func_name}"] = result
            except Exception as e:
                combined[f"result_{i+1}_{func_name}"] = {"error": str(e)}
    
    return {**state, "raw_db_results": combined}


# ── NODE 2c: execute_query_gen ────────────────────────────────────────────────
def execute_query_gen(state: AgentState) -> AgentState:
    history_text = build_history_text(state["chat_history"], limit=6)
    intent_description = state["intent"].get("intent", state["user_question"])
    
    schema_prompt = f"""You are a MongoDB aggregation pipeline expert for a time tracking system.
Generate ONLY a valid JSON aggregation pipeline array. No explanation. No markdown.
Just the raw JSON array starting with [ and ending with ].

DATABASE SCHEMA:

Collection: timeentries (TWO types — handle BOTH in every query)
  Type 1 (live): userId: ObjectId, projectId: ObjectId, startTime: Date, endTime: Date, duration: Number (seconds)
  Type 2 (imported): user: String (name), email: String, project: String, startDate: Date, endDate: Date, duration: Number (seconds)

Collection: users — _id: ObjectId, name: String, email: String, role: String
Collection: projects — _id: ObjectId, name: String, members: [ObjectId], status: String
Collection: groups — _id: ObjectId, name: String, memberIds: [ObjectId]
Collection: teams — _id: ObjectId, name: String, members: [ObjectId]

RULES (never break these):
- Date filter: always use $or covering both startTime and startDate
- User filter: check both userId (via $lookup on users) and user string field
- Project filter: check both projectId (via $lookup on projects) and project string field  
- Always exclude projects starting with "_INX-"
- Always include {{ $limit: 100 }}
- duration is SECONDS — divide by 3600 for hours, round to 2 decimal places
- Never use $out or $merge
- Return human-readable field names

CONVERSATION CONTEXT:
{history_text}

QUESTION: {intent_description}

Return ONLY the pipeline JSON array:"""

    try:
        try:
            gemini_model = genai.GenerativeModel(GEMINI_MODEL)
            response = gemini_model.generate_content(schema_prompt)
            text = response.text.strip()
        except Exception as gemini_err:
            # Fallback to Groq if Gemini hits quota/rate limits or fails
            strict_prompt = schema_prompt + "\n\nCRITICAL: You must output STRICT standard JSON. Every single key (especially MongoDB operators like $or, $match, $group, and field names like startTime, userId) MUST be enclosed in double quotes. Do not output JavaScript object literal format. Example: use \"$or\" instead of $or, and \"startTime\" instead of startTime."
            fallback_response = llm_classifier.invoke([
                {"role": "user", "content": strict_prompt}
            ])
            text = fallback_response.content.strip()
        
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            text = text[start_idx:end_idx + 1]
            
        # Clean up unquoted keys (JS-like object syntax) if any
        import re
        text = re.sub(r'(?<={|,)\s*([a-zA-Z_\$][a-zA-Z0-9_\$]*)\s*:', r'"\1":', text)
            
        pipeline = json.loads(text)
        
        # Safety validation
        is_safe, error_msg = validate_pipeline(pipeline)
        if not is_safe:
            return {**state, "raw_db_results": {"error": f"Unsafe pipeline blocked: {error_msg}"}}
        
        # Run on timeentries collection
        result = list(db["timeentries"].aggregate(pipeline))
        
        # Convert ObjectId to string for JSON serialization
        clean = []
        for doc in result:
            clean_doc = {}
            for k, v in doc.items():
                clean_doc[k] = str(v) if hasattr(v, '__str__') and not isinstance(v, (int, float, str, bool, list, dict)) else v
            clean.append(clean_doc)
        
        return {**state, "raw_db_results": {"query_results": clean, "count": len(clean)}}
    
    except Exception as e:
        return {**state, "raw_db_results": {"error": f"Query generation failed: {str(e)}"}}


# ── NODE 3: format_answer ─────────────────────────────────────────────────────
def format_answer(state: AgentState) -> AgentState:
    history_text = build_history_text(state["chat_history"], limit=6)
    
    # Handle direct answers (greetings etc)
    if state["path"] == "direct":
        return {**state, "final_response": state["intent"].get("answer", "Hello!")}
    
    raw = str(state.get("raw_db_results", {}))
    if len(raw) > 3000:
        raw = raw[:3000] + "... (truncated)"
    
    system_prompt = f"""You are a helpful analytics assistant for a company time tracking system.
Answer the manager's question in plain, natural English.

RULES:
- No markdown, no bold, no bullet points, no headers
- Write in plain sentences like a human colleague
- Use pronouns naturally based on conversation history
  (if we already discussed "Raj" you can say "he" or "Raj" naturally)
- If data shows hours, round to 1 decimal place in your answer
- If no data found, say so clearly and suggest rephrasing
- Keep answer concise — 1 to 4 sentences for simple questions
- For lists, write them as natural sentences: "Raj logged 8 hours, Sonu logged 6 hours, and Priya logged 4 hours."

CONVERSATION HISTORY:
{history_text}

DATA FROM DATABASE:
{raw}"""

    response = llm_formatter.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["user_question"]}
    ])
    
    return {**state, "final_response": response.content.strip()}


# ── ROUTER FUNCTION ───────────────────────────────────────────────────────────
def route_to_node(state: AgentState) -> str:
    path = state.get("path", "query_gen")
    if path == "executor":
        return "execute_known"
    elif path == "multi":
        return "execute_multi"
    elif path == "direct":
        return "format_answer"
    else:
        return "execute_query_gen"


# ── BUILD GRAPH ───────────────────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(AgentState)
    
    graph.add_node("intent_classifier", intent_classifier)
    graph.add_node("execute_known", execute_known)
    graph.add_node("execute_multi", execute_multi)
    graph.add_node("execute_query_gen", execute_query_gen)
    graph.add_node("format_answer", format_answer)
    
    graph.set_entry_point("intent_classifier")
    
    graph.add_conditional_edges(
        "intent_classifier",
        route_to_node,
        {
            "execute_known": "execute_known",
            "execute_multi": "execute_multi",
            "execute_query_gen": "execute_query_gen",
            "format_answer": "format_answer",
        }
    )
    
    graph.add_edge("execute_known", "format_answer")
    graph.add_edge("execute_multi", "format_answer")
    graph.add_edge("execute_query_gen", "format_answer")
    graph.add_edge("format_answer", END)
    
    return graph.compile()


compiled_graph = build_graph()


@traceable
def run_graph(user_question: str, chat_history: list = []) -> str:
    initial_state: AgentState = {
        "user_question": user_question,
        "chat_history": chat_history,
        "intent": None,
        "path": None,
        "raw_db_results": None,
        "final_response": None,
        "error_log": None,
        "retry_count": 0,
    }
    
    result = compiled_graph.invoke(initial_state)
    return result.get("final_response", "I could not find an answer. Please try rephrasing.")
