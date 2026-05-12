import os
import json
from groq import Groq
from config import GROQ_API_KEY, MODEL
import services.query_service as query_service
from tools.definitions import TOOLS

client = Groq(api_key=GROQ_API_KEY)

from datetime import datetime, timezone

today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")

SYSTEM_PROMPT = f"""Today's date is {today} (UTC).

You are Trackify AI, a friendly analytics assistant for a time-tracking tool called Trackify.

STRICT RULES:
- Always call the appropriate tool first before answering any data question
- If the tool returns an empty list [], respond with: "No entries found for that period."
- NEVER show raw data, JSON, dict objects, query strings, or code in your response
- NEVER say things like "based on available data" or "the query returned" or show {{'userName': 'x'}}
- Speak ONLY in plain English like a helpful human assistant
- Keep answers to 1-3 sentences maximum
- Use actual names and numbers from the tool result
- If you genuinely have no data, say so simply: "I couldn't find any data for that."
- If a user search returns [], say "No user named '[name]' was found in the system."
- If asked about data that doesn't exist, give a specific "not found" answer using the actual name/term they asked about
- Never say "No entries found for that period" for non-time questions

GOOD example: "User1 worked 5.75 hours today."
BAD example: "{{'userName': 'user1'}} 2026-05-12 Result is {{'hours': 5.75}}"
"""

def build_api_messages(messages):
    api_messages = []
    for m in messages:
        if m["role"] == "tool":
            api_messages.append({
                "role": "tool",
                "tool_call_id": m.get("tool_call_id"),
                "name": m.get("name"),
                "content": m["content"]
            })
        else:
            api_messages.append({"role": m["role"], "content": m["content"]})
            
    if not any(m["role"] == "system" for m in api_messages):
        api_messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
    else:
        for m in api_messages:
            if m["role"] == "system":
                m["content"] = SYSTEM_PROMPT
    return api_messages

def execute_tool(tool_name, tool_arguments=None):
    import json
    args = json.loads(tool_arguments) if tool_arguments else {}
    
    tool_map = {
        "get_all_users": lambda: query_service.get_all_users(),
        "get_total_hours_by_user": lambda: query_service.get_total_hours_by_user(),
        "get_hours_by_project": lambda: query_service.get_hours_by_project(),
        "get_entries_without_task": lambda: query_service.get_entries_without_task(),
        "get_active_timers": lambda: query_service.get_active_timers(),
        "get_project_list": lambda: query_service.get_project_list(),
        "get_user_hours_this_week": lambda: query_service.get_user_hours_this_week(),
        "get_hours_today": lambda: query_service.get_hours_today(),
        "search_user_by_name": lambda: query_service.search_user_by_name(args.get("name", "")),
    }
    func = tool_map.get(tool_name)
    if func:
        return func()
    return "Tool not found"

def chat(messages):
    api_messages = build_api_messages(messages)
    
    # First call - let LLM decide which tool to use
    response = client.chat.completions.create(
        model=MODEL,
        messages=api_messages,
        tools=TOOLS,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    
    # DEBUG PRINT
    print(f"\n[DEBUG] LLM Initial Response: {response_message}\n")
    
    # Check if LLM wants to call a tool
    if response_message.tool_calls:
        tool_call = response_message.tool_calls[0]
        tool_name = tool_call.function.name
        
        print(f"[DEBUG] Tool called: {tool_name}")
        
        # Execute the actual Python function
        result = execute_tool(tool_name, tool_call.function.arguments)
        
        print(f"[DEBUG] Tool: {tool_name}, Result type: {type(result)}, Result: {result}")
        
        print(f"[DEBUG] Tool result: {result}")
        
        # Build second call with tool result
        api_messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": tool_call.function.arguments
                    }
                }
            ]
        })
        
        api_messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": str(result)
        })
        
        # Second call - LLM formats the real data into human answer
        try:
            final_response = client.chat.completions.create(
                model=MODEL,
                messages=api_messages
            )
            return final_response.choices[0].message.content
        except Exception as e:
            print(f"[ERROR] Second LLM call failed: {e}")
            return "Sorry, I had trouble processing that. Please try again."
    
    # No tool needed - direct answer
    return response_message.content
