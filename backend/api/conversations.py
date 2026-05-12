from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict

router = APIRouter()

# In-memory storage for conversations
conversations_db: Dict[str, List[dict]] = {}

@router.get("/conversations/{session_id}")
async def get_conversation(session_id: str):
    return {"messages": conversations_db.get(session_id, [])}

@router.post("/conversations/{session_id}/clear")
async def clear_conversation(session_id: str):
    if session_id in conversations_db:
        conversations_db[session_id] = []
    return {"status": "cleared"}
