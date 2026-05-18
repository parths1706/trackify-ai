from groq import Groq
from config import GROQ_API_KEY, MODEL
from datetime import datetime, timezone
from tools.definitions import TOOLS
from tools import executors
import json

# Module-level Groq client — exported for use in chat.py streaming endpoint
client = Groq(api_key=GROQ_API_KEY)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def get_system_prompt():
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    return f"""You are Trackify AI, a friendly analytics assistant for a company time-tracking platform.
Today is {today} (UTC).

You have tools to query real company data. Rules:
- ALWAYS use a tool when the question involves hours, projects, employees, or productivity
- After getting tool results, give a clear human-friendly answer
- Show hours as numbers (e.g. "142.5 hours"), never in seconds
- Never show raw data, JSON, object IDs, or code to the user
- If a tool returns an error field, apologize briefly and explain what went wrong in plain English
- For questions not about data (greetings, general questions), answer directly without tools
- Keep answers concise: 2–5 sentences for simple questions, a short structured list for complex ones"""


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

TOOL_MAP = {
    "get_user_hours":           executors.get_user_hours,
    "get_user_projects":        executors.get_user_projects,
    "get_project_contributors": executors.get_project_contributors,
    "get_active_employees":     executors.get_active_employees,
    "get_project_stats":        executors.get_project_stats,
    "get_general_count":        executors.get_general_count,
}


def execute_tool(name: str, args: dict) -> dict:
    """Safely dispatch a tool call to its Python executor."""
    fn = TOOL_MAP.get(name)
    if not fn:
        return {"error": f"Unknown tool: {name}"}
    try:
        return fn(**args)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}


# ---------------------------------------------------------------------------
# Message builder (exported for chat.py streaming endpoint)
# ---------------------------------------------------------------------------

def build_api_messages(messages: list) -> list:
    """Build the messages list for the Groq API call.
    Prepends the system prompt and keeps only the last 6 user/assistant turns.
    """
    api_msgs = [{"role": "system", "content": get_system_prompt()}]
    recent = messages[-6:] if len(messages) > 6 else messages
    for m in recent:
        if isinstance(m, dict) and m.get("role") in ["user", "assistant"]:
            api_msgs.append({"role": m["role"], "content": str(m.get("content", ""))})
    return api_msgs


# ---------------------------------------------------------------------------
# Primary chat function (called by /chat endpoint as sync_chat)
# ---------------------------------------------------------------------------

def chat(messages: list) -> str:
    """Process a chat request using function-calling architecture.

    Flow:
      1. Ask LLM which tool to use (or answer directly if no tool needed)
      2. Execute the chosen tool via Python executor (up to MAX_TOOL_CALLS times)
      3. Send tool result back to LLM for natural language formatting
      4. Return the final human-readable response
    """
    api_messages = build_api_messages(messages)

    MAX_TOOL_CALLS = 3
    tool_call_count = 0

    while tool_call_count < MAX_TOOL_CALLS:
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=api_messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=1000
            )
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            return "I'm having trouble right now. Please try a simpler question."

        assistant_message = response.choices[0].message

        # No tool call — return the direct answer
        if not assistant_message.tool_calls:
            return assistant_message.content

        tool_call = assistant_message.tool_calls[0]
        tool_call_count += 1

        try:
            arguments = json.loads(tool_call.function.arguments)
        except Exception:
            return "I had trouble understanding that request. Please rephrase."

        function_name = tool_call.function.name
        print(f"[DEBUG] Tool call {tool_call_count}: {function_name}({arguments})")

        tool_result = execute_tool(function_name, arguments)
        print(f"[DEBUG] Tool result: {tool_result}")

        # Append assistant message (with tool_calls) and tool result to history
        api_messages.append(assistant_message)
        api_messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(tool_result)
        })

        # If the tool returned an error, let the LLM formulate the apology
        if "error" in tool_result:
            break

    # Ask LLM to format the final answer (no tools on this call)
    try:
        final = client.chat.completions.create(
            model=MODEL,
            messages=api_messages,
            max_tokens=500
        )
        return final.choices[0].message.content
    except Exception as e:
        return f"Sorry, I ran into an issue: {str(e)}"
