"""
FastAPI router integration for the chatbot module.
"""

import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Literal

from .service import process_chat
from .config import set_db_engine
from .rag import get_vectorstore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chatbot"])


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    source: Literal["rag", "sql", "hybrid"]
    details: dict = {}


# ── Auth (keep your existing) ──────────────────────────────────
from app.routers.auth import get_current_user
from app.models.user import User

async def require_auth(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    user: dict = Depends(require_auth),
):
    logger.debug("Chat request: %s", req.question)
    try:
        result = process_chat(req.question)
        logger.debug("Chat result: %s", result.get("source"))
        return ChatResponse(**result)
    except Exception as e:
        logger.error("CHATBOT 500:\n%s", traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne : {str(e)}"
        )


def init_chatbot(db_engine):
    """
    Call this in your FastAPI startup event.
    """
    try:
        set_db_engine(db_engine)
        logger.info("DB engine injected into chatbot")
    except Exception as e:
        logger.error("Failed to set DB engine: %s", e)
        raise

    try:
        vs = get_vectorstore()
        logger.info("Vectorstore ready")
    except Exception as e:
        logger.error("Vectorstore init failed: %s", e)
        raise