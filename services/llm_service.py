import os
import json
from groq import Groq
from config import GROQ_API_KEY, MODEL
import services.query_service as query_service
from tools.definitions import TOOLS

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are Trackify AI, a precise analytics assistant for a time-tracking platform called Trackify.

STRICT RULES:
- You MUST use the provided tools to fetch real data before answering ANY question about users, hours, projects, or tasks
- NEVER make up users, hours, projects, or any numbers
- NEVER say "I don't have a database" — you do, via tools
- If a tool returns empty data, say "No data found for that query"
- After getting tool results, answer in friendly natural human language
- Be conversational, warm, and specific — use actual names and numbers from the data
- Keep answers concise — 2 to 4 sentences max unless listing items
- For greetings or non-data questions, respond normally without using tools"""

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

def execute_tool(tool_name):
    tool_map = {
        "get_all_users": query_service.get_all_users,
        "get_total_hours_by_user": query_service.get_total_hours_by_user,
        "get_hours_by_project": query_service.get_hours_by_project,
        "get_entries_without_task": query_service.get_entries_without_task,
        "get_active_timers": query_service.get_active_timers,
        "get_project_list": query_service.get_project_list,
        "get_user_hours_this_week": query_service.get_user_hours_this_week,
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
        result = execute_tool(tool_name)
        
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
        final_response = client.chat.completions.create(
            model=MODEL,
            messages=api_messages
        )
        
        return final_response.choices[0].message.content
    
    # No tool needed - direct answer
    return response_message.content
