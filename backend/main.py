from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import chat, conversations, feedback

app = FastAPI(title="Trackify AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(chat.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}

