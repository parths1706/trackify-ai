from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json

from services.llm_service import client, build_api_messages, chat as sync_chat, TOOLS, execute_tool
from config import MODEL
from api.conversations import conversations_db

router = APIRouter()

class ChatRequest(BaseModel):
    messages: List[dict]
    session_id: Optional[str] = None

@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    if req.session_id:
        conversations_db[req.session_id] = req.messages
        
    try:
        reply = sync_chat(req.messages)
        if req.session_id:
            conversations_db[req.session_id].append({"role": "assistant", "content": reply})
        return {"reply": reply}
    except Exception as e:
        error_msg = str(e)
        if "400" in error_msg:
            error_msg = "The AI had trouble generating the database query. Please try rephrasing your question."
        return {"reply": f"Error: {error_msg}"}

@router.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    if req.session_id:
        conversations_db[req.session_id] = req.messages

    def generate_stream():
        try:
            api_messages = build_api_messages(req.messages)
            
            # First call to check for tool usage
            response = client.chat.completions.create(
                model=MODEL,
                messages=api_messages,
                tools=TOOLS,
                tool_choice="auto",
                stream=False
            )
            
            response_message = response.choices[0].message
            
            if response_message.tool_calls:
                tool_call = response_message.tool_calls[0]
                args = json.loads(tool_call.function.arguments)
                function_name = tool_call.function.name

                result = execute_tool(function_name, args)

                api_messages.append(response_message)
                api_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })
                
                # Second call - stream the final response
                stream = client.chat.completions.create(
                    model=MODEL,
                    messages=api_messages,
                    stream=True
                )
                
                full_response = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield f"data: {json.dumps({'content': content})}\n\n"
                        
                if req.session_id:
                    conversations_db[req.session_id].append({"role": "assistant", "content": full_response})
                    
            else:
                # No tool call, stream directly
                stream = client.chat.completions.create(
                    model=MODEL,
                    messages=api_messages,
                    stream=True
                )
                
                full_response = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield f"data: {json.dumps({'content': content})}\n\n"
                        
                if req.session_id:
                    conversations_db[req.session_id].append({"role": "assistant", "content": full_response})
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            if "400" in str(e):
                error_msg = "The AI had trouble generating the database query. Please try rephrasing your question."
            yield f"data: {json.dumps({'content': error_msg})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")
