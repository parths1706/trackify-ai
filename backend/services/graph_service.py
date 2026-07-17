import json
import re
import os
from datetime import datetime
from bson.json_util import loads as bson_loads
from google import genai as google_genai
from google.genai import types as genai_types
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langsmith import traceable
from schemas.state import AgentState
from tools.executors import (
    get_user_hours, get_user_projects, get_project_contributors,
    get_active_employees, get_project_stats, get_general_count,
    get_user_recent_activity, get_idle_employees, get_user_project_hours,
    validate_pipeline
)
from config import GROQ_API_KEY, GROQ_MODEL_LARGE, GROQ_MODEL_SMALL
from database import db

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
    "get_user_project_hours":   get_user_project_hours,
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
    current_date_str = datetime.now().strftime("%A, %B %d, %Y")
    
    system_prompt = f"""You are an intent classifier for a time tracking analytics system.

CURRENT DATE CONTEXT:
Today is {current_date_str}.

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
- get_idle_employees(days) — employees with no hours in last N days (prefer this for "who has not logged hours", "who is idle", or "who has 0 hours")
- get_user_project_hours(user_name, start_date, end_date, limit) — use when asked which projects someone worked on in a period, or hours breakdown by project for a person
CRITICAL RULES FOR INTENT REWRITING:
- You MUST preserve ALL date and time references from the conversation history exactly as stated. Examples: "this month", "last week", "today", "last quarter", "this year". Never drop or omit them.
- You MUST resolve all pronouns ("them", "they", "their", "it") to the actual entity names found in conversation history.
- The rewritten intent must be a fully self-contained sentence that includes: WHO (user/team name), WHAT (metric), and WHEN (time period or "no date filter" if none mentioned).
- If the previous message mentioned a time period and the new message does not contradict it, carry it forward.

ROUTING RULES:
- If the question mentions a team name (e.g. "Design team", "Python team") → always route to a team-based executor or query_gen, never to a user-specific executor like get_user_hours or resolve_user.
- If the question mentions a person's name or pronoun referring to a single person → route to user-specific executors.
- If the question contains "compare this week" or "vs last week" or "this week and last week" with NO person name mentioned → always route to query_gen, never to any user executor.
- If the question asks "who worked on [project name]" or "which employees worked on [project]" or "hours logged on [project name]" → always route to query_gen. Never route to a user executor. This is a project-based lookup, not a user lookup.
- If unsure whether the subject is a person or a team → route to query_gen, not a user executor.

INSTRUCTIONS:
1. Use conversation history to resolve pronouns (he/she/him/they/same/that/it)
2. Always resolve relative dates (e.g., "this week", "this month", "last month", "today", "yesterday") to exact YYYY-MM-DD date strings in the parameters.
   Use the CURRENT DATE CONTEXT ({current_date_str}) to calculate these date strings:
   - "this month" or "this month's hours" -> start_date: "2026-06-01", end_date: "2026-06-30"
   - "this week" -> start_date: "2026-06-15" (Monday), end_date: "2026-06-21" (Sunday)
   - "yesterday" -> start_date: "2026-06-15", end_date: "2026-06-15"
3. Any query involving teams or groups of employees (e.g., "team design", "Team QA", "Team Python", "members of Team Backend") must use PATH C ("query_gen") because there are no executors for team-level aggregations or comparisons.
4. Choose ONE of five output paths:

PATH A — single known executor fits the question:
{{"path": "executor", "function": "function_name", "params": {{...}}}}

PATH B — question needs 2-3 executor calls combined:
{{"path": "multi", "steps": [{{"function": "...", "params": {{...}}}}, {{"function": "...", "params": {{...}}}}]}}

PATH C — question is too complex or does not match any executor:
{{"path": "query_gen", "intent": "plain English description of exactly what data is needed"}}

PATH D — greeting or non-data question:
{{"path": "direct", "answer": "your response here"}}

PATH E — clarify
{{"path": "clarify", "intent": "user message"}}
Use this path when the user's message is ambiguous, unclear, a correction, a disagreement, or doesn't clearly map to a data question. Examples: "should be 8", "that doesn't look right", "no that's wrong", "huh?", "what do you mean", or any short reactive message that isn't a new question or a greeting.
Never default to greeting or query_gen for these — always use clarify.

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
    
    if intent.get("path") in ["executor", "multi"]:
        intent_str = str(intent).lower()
        if "team" in intent_str or "group" in intent_str:
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
    today = datetime.now().strftime("%Y-%m-%d")

    schema_prompt = f"""You are a MongoDB aggregation pipeline expert.
Generate ONLY a valid JSON array for MongoDB aggregation. No explanation. No markdown. Start with [ end with ].

DATABASE SCHEMA:
EXACT COLLECTION FIELD NAMES — always use these, never guess:
- timeentries: {{ _id, userId (ObjectId), projectId (ObjectId), entryDate (date field — always filter dates using this), duration (number, in hours), billable (boolean) }}
- users: {{ _id, name (string) }}
- projects: {{ _id, name (string) }}
- groups: {{ _id, name (string), memberIds: [ObjectId] }}

For project name matching ALWAYS use case-insensitive regex:
{{"$regex": "beva", "$options": "i"}} — never exact string match on project or user names.

To query hours for a team named "Design", you must use a reverse $lookup from timeentries, because the DB runs a single pipeline on timeentries:
{{ "$lookup": {{ "from": "groups", "localField": "userId", "foreignField": "memberIds", "as": "matched_group" }} }}
{{ "$match": {{ "matched_group.name": {{ "$regex": "Design", "$options": "i" }} }} }}

ANTI-JOIN PATTERN — use this when asked "which projects had zero hours" or "who hasn't logged":
To find projects with zero hours logged this week:
1. $lookup timeentries into projects on _id = projectId with date filter in pipeline
2. $match where the looked-up array is empty: {{ "entries": {{ "$size": 0 }} }}
Never return user names when asked about projects. Always verify the collection you are grouping on matches what was asked.

WEEK COMPARISON PATTERN — when asked to compare this week vs last week with no specific user mentioned:
- This is NOT a user query. Never route to a user executor.
- Generate a single pipeline on timeentries that groups by week using $isoWeek or by date range.
- This week: entryDate >= [monday of current week], entryDate <= today
- Last week: entryDate >= [monday of previous week], entryDate < [monday of current week]
- Group both periods separately using $facet or two $group stages, then return both totals.

DATE CALCULATION RULES:
- If the user does NOT mention any date or time period, do NOT add any date filter to the pipeline. Query all available data with no $match on entryDate.
- Only add entryDate filters when the user explicitly says words like: "this week", "last month", "today", "this month", "last week", "this year", or a specific date.
- "last month" = first day of previous calendar month to last day of previous calendar month.
  Example: if today is 2026-06-29, last month = 2026-05-01 to 2026-05-31.
- "this month" = first day of current month to today.
- "last week" = Monday to Sunday of the previous week.
- "this week" = Monday of current week to today.
- Always calculate these relative to TODAY: {today}
- Never say "I don't have data for last month" unless the query genuinely returns empty after correct date filtering.

PIPELINE EXAMPLES — always follow these exact structures:

EXAMPLE 1: "Who worked on Beva web app and how many hours did each person log?"
Root collection: timeentries (ALWAYS start from timeentries)
[
  {{ "$lookup": {{ "from": "projects", "localField": "projectId", "foreignField": "_id", "as": "projectInfo" }} }},
  {{ "$unwind": "$projectInfo" }},
  {{ "$match": {{ "projectInfo.name": {{ "$regex": "Beva", "$options": "i" }} }} }},
  {{ "$group": {{ "_id": "$userId", "totalDuration": {{ "$sum": "$duration" }}, "projectName": {{ "$first": "$projectInfo.name" }} }} }},
  {{ "$lookup": {{ "from": "users", "localField": "_id", "foreignField": "_id", "as": "userInfo" }} }},
  {{ "$unwind": "$userInfo" }},
  {{ "$project": {{ "_id": 0, "userName": "$userInfo.name", "projectName": "$projectName", "queryPeriod": "all time", "totalHours": {{ "$round": [{{ "$divide": ["$totalDuration", 3600] }}, 2] }} }} }}
]

EXAMPLE 2: "Which project had the most hours logged by the PHP team last month?"
Root collection: timeentries (ALWAYS start from timeentries)
[
  {{ "$match": {{ "entryDate": {{ "$gte": {{ "$date": "2026-05-01T00:00:00.000Z" }}, "$lte": {{ "$date": "2026-05-31T23:59:59.999Z" }} }} }} }},
  {{ "$lookup": {{ "from": "groups", "localField": "userId", "foreignField": "memberIds", "as": "matched_group" }} }},
  {{ "$match": {{ "matched_group.name": {{ "$regex": "PHP", "$options": "i" }} }} }},
  {{ "$group": {{ "_id": "$projectId", "totalDuration": {{ "$sum": "$duration" }}, "teamName": {{ "$first": {{ "$arrayElemAt": ["$matched_group.name", 0] }} }} }} }},
  {{ "$lookup": {{ "from": "projects", "localField": "_id", "foreignField": "_id", "as": "projectInfo" }} }},
  {{ "$unwind": "$projectInfo" }},
  {{ "$match": {{ "projectInfo.name": {{ "$not": {{ "$regex": "^_INX-" }} }} }} }},
  {{ "$sort": {{ "totalDuration": -1 }} }},
  {{ "$limit": 1 }},
  {{ "$project": {{ "_id": 0, "projectName": "$projectInfo.name", "teamName": "$teamName", "totalHours": {{ "$round": [{{ "$divide": ["$totalDuration", 3600] }}, 2] }} }} }}
]

CRITICAL RULE: timeentries is ALWAYS the root collection. You NEVER start a pipeline from users, projects, or groups. You always start from timeentries and $lookup outward to users, projects, or groups. Starting from any other collection is always wrong.

IMPORTANT: In the final $project stage of any pipeline, always include these context fields so the formatter knows what was queried:
- "teamName": {{ "$arrayElemAt": ["$matched_group.name", 0] }} — include when query involves a team
- "projectName": "$projectInfo.name" — include when query involves a project  
- "userName": "$userInfo.name" — include when query involves a user
Never strip context fields in $project. The formatter needs them to construct an accurate response.

RULES:
- entryDate is THE ONLY date field.
- For date values, use MongoDB Extended JSON format: {{"$date": "YYYY-MM-DDTHH:MM:SS.000Z"}}. Never use raw ISODate("...") or other helper functions.
- Always use $lookup to join users/projects by ObjectId.
- To filter by team: lookup groups collection using the reverse $lookup pattern shown above.
- Always exclude projects with name starting with _INX-.
- duration in seconds, divide by 3600 for hours, round 2 decimals.
- Always add $limit: 100 at end.
- Today is {today}.

STRICT OUTPUT RULES:
- ALWAYS start every pipeline from the timeentries collection. Never start from users, projects, or groups.
- Always include a "queryPeriod" field in the final $project stage describing what time period was queried. Examples: "queryPeriod": "last month (May 2026)", "queryPeriod": "this week", "queryPeriod": "all time". This helps the formatter give accurate responses without guessing.
- Output only valid JSON. No JavaScript syntax.
- Never use regex literals like /pattern/. Always use {{"$regex": "^pattern", "$options": "i"}} instead.
- Never use ObjectId("...") syntax. Use the raw string ID directly.
- Never use ISODate(). Use ISO string format like "2026-06-01".
- For excluding _INX- projects always use: {{"$not": {{"$regex": "^_INX-"}}}}
- Never use $project to strip identifying context (team name, project name, user name) from results. Always carry them through to the final output so the answer formatter can reference them accurately.

CONVERSATION HISTORY (use this to resolve pronouns, dates, and context from previous messages):
{history_text}

QUESTION: {intent_description}

Return ONLY the JSON array:"""

    text = None
    
    # Try Gemini first
    try:
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if gemini_key:
            client = google_genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=schema_prompt,
                config=genai_types.GenerateContentConfig(
                    thinking_config=genai_types.ThinkingConfig(thinking_budget=0)
                )
            )
            text = response.text.strip()
    except Exception as gemini_err:
        text = None

    # Fallback to Groq if Gemini failed
    if not text:
        try:
            groq_response = llm_classifier.invoke([
                {"role": "user", "content": schema_prompt + "\n\nReturn ONLY a valid JSON array starting with [. Wrap all operators and keys in double quotes."}
            ])
            text = groq_response.content.strip()
        except Exception as groq_err:
            return {**state, "raw_db_results": {"error": "Query generation failed"}, "query_status": "failed", "error_message": "Query generation failed", "raw_pipeline": "", "retry_count": 0}

    try:
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        if start_idx == -1 or end_idx == -1:
            return {**state, "raw_db_results": {"error": "No valid pipeline found in response"}, "query_status": "failed", "error_message": "No valid pipeline found in response", "raw_pipeline": "", "retry_count": 0}
        
        text = text[start_idx:end_idx + 1]
        
        # Clean up Mongo-specific wrappers to strict JSON
        text = re.sub(r'ISODate\("([^"]+)"\)', r'{"$date": "\1"}', text)
        text = re.sub(r'ObjectId\("([^"]+)"\)', r'{"$oid": "\1"}', text)
        
        # Quote unquoted keys (e.g., $match: -> "$match":)
        text = re.sub(r'(?<={|,)\s*([a-zA-Z_\$][a-zA-Z0-9_\$]*)\s*:', r'"\1":', text)
        text = re.sub(r'^\s*([a-zA-Z_\$][a-zA-Z0-9_\$]*)\s*:', r'"\1":', text, flags=re.MULTILINE)
        
        try:
            pipeline = bson_loads(text)
        except Exception as parse_err:
            return {
                **state,
                "raw_db_results": {
                    "status": "parse_error",
                    "message": "Pipeline generation failed",
                    "raw": text
                },
                "query_status": "failed",
                "error_message": "Pipeline generation failed",
                "raw_pipeline": text,
                "retry_count": 0
            }
        
        is_safe, error_msg = validate_pipeline(pipeline)
        if not is_safe:
            return {**state, "raw_db_results": {"error": f"Unsafe pipeline: {error_msg}"}, "query_status": "failed", "error_message": f"Unsafe pipeline: {error_msg}", "raw_pipeline": text, "retry_count": 0}

        result = list(db.timeentries.aggregate(pipeline, maxTimeMS=15000))

        clean = []
        for doc in result:
            clean_doc = {}
            for k, v in doc.items():
                if hasattr(v, 'id'):
                    clean_doc[k] = str(v)
                elif isinstance(v, datetime):
                    clean_doc[k] = v.strftime("%Y-%m-%d")
                else:
                    clean_doc[k] = v
            clean.append(clean_doc)

        return {**state, "raw_db_results": {"query_results": clean, "count": len(clean)}, "query_status": "success", "raw_pipeline": text, "retry_count": 0, "error_message": ""}

    except Exception as e:
        return {**state, "raw_db_results": {"error": f"Pipeline execution failed: {str(e)}"}, "query_status": "failed", "error_message": f"Pipeline execution failed: {str(e)}", "raw_pipeline": text, "retry_count": 0}




# ── NODE: correct_query_gen ───────────────────────────────────────────────────
def correct_query_gen(state: AgentState) -> AgentState:
    history_text = build_history_text(state["chat_history"], limit=6)
    intent_description = state["intent"].get("intent", state["user_question"])
    failed_pipeline = state.get("raw_pipeline", "")
    error_message = state.get("error_message", "Unknown error")
    today = datetime.now().strftime("%Y-%m-%d")

    correction_prompt = f"""You are a MongoDB aggregation pipeline expert.
Your previous pipeline attempt failed. You must fix it.

FAILED PIPELINE:
{failed_pipeline}

ERROR MESSAGE:
{error_message}

CONVERSATION HISTORY:
{history_text}

QUESTION: {intent_description}
TODAY: {today}

STRICT OUTPUT RULES:
- ALWAYS start every pipeline from the timeentries collection. Never start from users, projects, or groups.
- Always include a "queryPeriod" field in the final $project stage describing what time period was queried. Examples: "queryPeriod": "last month (May 2026)", "queryPeriod": "this week", "queryPeriod": "all time". This helps the formatter give accurate responses without guessing.
- Output only valid JSON array. Nothing else. No explanation.
- Never use JavaScript regex literals like /pattern/. Always use {{"$regex": "pattern", "$options": "i"}}.
- Never use ObjectId(), ISODate(), or any JS syntax.
- For excluding _INX- projects always use: {{"projectName": {{"$not": {{"$regex": "^_INX-"}}}}}}
- For team lookups always use $lookup from timeentries to groups on localField userId foreignField memberIds.
- Never use $project to strip identifying context (team name, project name, user name) from results. Always carry them through to the final output so the answer formatter can reference them accurately.

Return only the corrected pipeline JSON array."""

    try:
        response = llm_classifier.invoke([
            {"role": "user", "content": correction_prompt}
        ])
        raw = response.content.strip()
    except Exception as e:
        return {**state, "query_status": "failed", "error_message": str(e), "retry_count": state.get("retry_count", 0) + 1}

    try:
        start_idx = raw.find('[')
        end_idx = raw.rfind(']')
        if start_idx != -1 and end_idx != -1:
            raw = raw[start_idx:end_idx + 1]
            
        raw = re.sub(r'ISODate\("([^"]+)"\)', r'{"$date": "\1"}', raw)
        raw = re.sub(r'ObjectId\("([^"]+)"\)', r'{"$oid": "\1"}', raw)
        raw = re.sub(r'(?<={|,)\s*([a-zA-Z_\$][a-zA-Z0-9_\$]*)\s*:', r'"\1":', raw)
        raw = re.sub(r'^\s*([a-zA-Z_\$][a-zA-Z0-9_\$]*)\s*:', r'"\1":', raw, flags=re.MULTILINE)

        pipeline = bson_loads(raw)
        is_safe, err_msg = validate_pipeline(pipeline)
        if not is_safe:
            raise Exception(f"Unsafe pipeline: {err_msg}")
            
        result = list(db.timeentries.aggregate(pipeline, maxTimeMS=15000))
        clean = []
        for doc in result:
            clean_doc = {}
            for k, v in doc.items():
                if hasattr(v, 'id'):
                    clean_doc[k] = str(v)
                elif isinstance(v, datetime):
                    clean_doc[k] = v.strftime("%Y-%m-%d")
                else:
                    clean_doc[k] = v
            clean.append(clean_doc)
            
        return {**state, "raw_db_results": {"query_results": clean, "count": len(clean)}, "query_status": "success", "retry_count": state.get("retry_count", 0) + 1}
    except Exception as e:
        return {
            **state,
            "raw_db_results": {
                "status": "parse_error",
                "message": "Pipeline correction failed",
                "raw": raw
            },
            "query_status": "failed",
            "error_message": str(e),
            "retry_count": state.get("retry_count", 0) + 1
        }

def route_after_query_gen(state: AgentState) -> str:
    if state.get("query_status") == "failed" and state.get("retry_count", 0) < 1:
        return "correct_query_gen"
    return "format_answer"

# ── NODE 3: format_answer ─────────────────────────────────────────────────────
def format_answer(state: AgentState) -> AgentState:
    history_text = build_history_text(state["chat_history"], limit=6)
    
    # Handle direct answers
    if state["path"] == "direct":
        return {**state, "final_response": state["intent"].get("answer", "Hello!")}
    
    raw_results = state.get("raw_db_results", {})
    if isinstance(raw_results, dict):
        if raw_results.get("status") == "parse_error":
            return {**state, "final_response": "I had trouble processing that query, please try rephrasing."}
        if raw_results.get("status") == "no_data":
            return {**state, "final_response": "I couldn't find any records matching your query. The data may not exist for the specified time period or team."}
    
    raw = str(raw_results)
    if len(raw) > 3000:
        raw = raw[:3000] + "... (truncated)"
    
    system_prompt = f"""You are a helpful analytics assistant for a company time tracking system.
Answer the manager's question in plain, natural English.

RULES:
- No markdown, no bold, no bullet points, no headers
- Write in plain sentences like a human colleague
- Use pronouns naturally based on conversation history
- If data shows hours, round to 1 decimal place in your answer
- Keep answer concise — 1 to 4 sentences for simple questions
- For lists of 1 to 5 items, write them as natural sentences (e.g. "Raj logged 8 hours, Sonu logged 6 hours, and Priya logged 4 hours.")
- For long lists of items or names (more than 5), do NOT list all of them. State the total count clearly and list only 3 to 5 examples (e.g., "There are 181 employees who did not log hours this week, including Aesha Patel, Aiyub Munshi, and Akash Patel.")
- If the data contains a "queryPeriod" field, use it to describe the time period in your answer naturally.
- If the data contains a "projectName" field, always mention the project name in your answer.
- If the data contains a "teamName" field, always mention the team name in your answer.

CRITICAL: If the DATA FROM DATABASE section contains ANY array or object with fields like userName, totalHours, projectName, teamName, or any numeric values — that IS valid data. You MUST answer the question using that data. Never say "I couldn't find" or "no data" or suggest rephrasing when data is present. Only say no data was found if the database returned an empty array [] or the status field is "no_data".

CONVERSATION HISTORY:
{history_text}

DATA FROM DATABASE:
{raw}"""

    response = llm_formatter.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["user_question"]}
    ])
    
    response_content = response.content.strip()
    return {**state, "final_response": response_content, "chat_history": [{"role": "assistant", "content": response_content}]}


# ── NODE 4: handle_clarify ────────────────────────────────────────────────────
def handle_clarify(state: AgentState) -> AgentState:
    history_text = build_history_text(state["chat_history"], limit=6)
    user_question = state["user_question"]

    clarify_prompt = f"""You are Trackify AI, a time-tracking analytics assistant.
The user sent an unclear or reactive message that doesn't map to a specific data question.

CONVERSATION HISTORY:
{history_text}

USER MESSAGE: {user_question}

Write a short, natural, helpful clarifying question. If they seem to be disagreeing with a previous answer, ask what they expected or what might be different about their calculation. If their message is vague, ask what specifically they want to know. Keep it 1-2 sentences, conversational, no markdown."""

    response = llm_formatter.invoke(clarify_prompt)
    response_content = response.content.strip()
    return {**state, "final_response": response_content, "chat_history": [{"role": "assistant", "content": response_content}]}


# ── ROUTER FUNCTION ───────────────────────────────────────────────────────────
def route_to_node(state: AgentState) -> str:
    path = state.get("path", "query_gen")
    if path == "executor":
        return "execute_known"
    elif path == "multi":
        return "execute_multi"
    elif path == "direct":
        return "format_answer"
    elif path == "clarify":
        return "handle_clarify"
    else:
        return "execute_query_gen"


# ── BUILD GRAPH ───────────────────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(AgentState)
    
    graph.add_node("intent_classifier", intent_classifier)
    graph.add_node("execute_known", execute_known)
    graph.add_node("execute_multi", execute_multi)
    graph.add_node("execute_query_gen", execute_query_gen)
    graph.add_node("correct_query_gen", correct_query_gen)
    graph.add_node("format_answer", format_answer)
    graph.add_node("handle_clarify", handle_clarify)
    
    graph.set_entry_point("intent_classifier")
    
    graph.add_conditional_edges(
        "intent_classifier",
        route_to_node,
        {
            "execute_known": "execute_known",
            "execute_multi": "execute_multi",
            "execute_query_gen": "execute_query_gen",
            "format_answer": "format_answer",
            "handle_clarify": "handle_clarify",
        }
    )
    
    graph.add_edge("execute_known", "format_answer")
    graph.add_edge("execute_multi", "format_answer")
    graph.add_conditional_edges("execute_query_gen", route_after_query_gen, {"correct_query_gen": "correct_query_gen", "format_answer": "format_answer"})
    graph.add_edge("correct_query_gen", "format_answer")
    graph.add_edge("format_answer", END)
    graph.add_edge("handle_clarify", END)
    
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


compiled_graph = build_graph()


@traceable
def run_graph(user_question: str, session_id: str = "default_thread") -> str:
    initial_state: AgentState = {
        "user_question": user_question,
        "chat_history": [{"role": "user", "content": user_question}],
        "intent": None,
        "path": None,
        "generated_pipeline": None,
        "target_collection": None,
        "raw_db_results": None,
        "final_response": None,
        "error_log": None,
        "retry_count": 0,
    }
    
    config = {"configurable": {"thread_id": session_id}}
    result = compiled_graph.invoke(initial_state, config=config)
    return result.get("final_response", "I could not find an answer. Please try rephrasing.")
