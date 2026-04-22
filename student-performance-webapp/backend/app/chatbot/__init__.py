"""
FastAPI router integration for the chatbot module.
Import and include this in your main FastAPI app.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal

# Import your existing auth dependency
# from app.auth import get_current_user  # Adjust path to your project

from .service import process_chat
from .config import set_db_engine
from .rag import get_vectorstore  # triggers init

router = APIRouter(prefix="/chat", tags=["chatbot"])


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    source: Literal["rag", "sql", "hybrid"]
    details: dict = {}


# ── Replace with your actual auth dependency ─────────────────────
from app.routers.auth import get_current_user
from app.models.user import User

async def require_auth(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    user: dict = Depends(require_auth),
):
    """
    Hybrid RAG + SQL chat endpoint.
    Protected by existing JWT auth.
    """
    # Optional: role-based restrictions
    # if user.get("role") not in ("director", "parent"):
    #     raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        result = process_chat(req.question)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def init_chatbot(db_engine):
    """
    Call this in your FastAPI startup event.
    Ensures Chroma is warmed up and DB engine is shared.
    """
    set_db_engine(db_engine)
    # Warm up vectorstore (loads or creates Chroma index)
    get_vectorstore()