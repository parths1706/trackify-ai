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
            response = sync_chat(req.messages)
            yield f"data: {json.dumps({'content': response})}\n\n"
            if req.session_id:
                conversations_db[req.session_id].append({"role": "assistant", "content": response})
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            yield f"data: {json.dumps({'content': error_msg})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")

