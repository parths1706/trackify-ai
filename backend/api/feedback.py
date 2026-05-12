# pyrefly: ignore [missing-import]
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
# Assuming we will use the existing database connection from database.py or motor
import database

router = APIRouter()

class FeedbackRequest(BaseModel):
    message_id: str
    session_id: str
    rating: str
    comment: str = ""

@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    if hasattr(database, 'db') and database.db is not None:
        database.db.feedback.insert_one({
            "message_id": req.message_id,
            "session_id": req.session_id,
            "rating": req.rating,
            "comment": req.comment,
            "created_at": datetime.utcnow()
        })
    return {"status": "feedback saved"}
