"""
Chatbot configuration — reuses existing SQLAlchemy engine.
Import your existing engine from your db module and pass it here.
"""

import os
from typing import Optional
from sqlalchemy.engine import Engine
from langchain_ollama import OllamaEmbeddings, ChatOllama
# ── Ollama Configuration ─────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "mistral")      # or llama3
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# ── LangChain Models ─────────────────────────────────────────────
embeddings = OllamaEmbeddings(
    model=OLLAMA_EMBED_MODEL,
    base_url=OLLAMA_BASE_URL,
)

llm = ChatOllama(
    model=OLLAMA_CHAT_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0.0,  # Deterministic for analytics
)

# ── Database (injected from existing app) ────────────────────────
# Your existing FastAPI app already creates an engine.
# We'll accept it via dependency injection in service.py.
_db_engine: Optional[Engine] = None

def set_db_engine(engine: Engine) -> None:
    global _db_engine
    _db_engine = engine

def get_db_engine() -> Engine:
    if _db_engine is None:
        raise RuntimeError("DB engine not set. Call set_db_engine() in main.py startup.")
    return _db_engine