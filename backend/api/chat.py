# pyrefly: ignore [missing-import]
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json

from services.llm_service import client, build_api_messages, execute_tool, chat as sync_chat
from tools.definitions import TOOLS
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
        
    reply = sync_chat(req.messages)
    
    if req.session_id:
        conversations_db[req.session_id].append({"role": "assistant", "content": reply})
        
    return {"reply": reply}

@router.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    if req.session_id:
        conversations_db[req.session_id] = req.messages

    def generate_stream():
        api_messages = build_api_messages(req.messages)
        
        # We make a non-streaming call first to easily check for tool usage
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
            tool_name = tool_call.function.name
            result = execute_tool(tool_name)
            
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
            # No tool call, we make a streaming call directly since we know there's no tools needed now.
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
                
    return StreamingResponse(generate_stream(), media_type="text/event-stream")
