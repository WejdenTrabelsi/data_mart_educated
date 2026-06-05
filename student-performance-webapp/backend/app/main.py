import os
import sys
import logging
import httpx

os.environ["PYTHONUTF8"] = "1"
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.auth import router as auth_router
from .routers.dashboard import router as dashboard_router
from .models.user import Base
from .database import engine
from .routers import suggestions
from .chatbot import router as chatbot_router, init_chatbot

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Student Performance API",
    description="Backend for Admin Dashboard",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(chatbot_router)
app.include_router(suggestions.router)


@app.on_event("startup")
async def startup_event():
    # 1. SQL tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ SQL tables verified")
    except Exception as e:
        logger.error("❌ SQL table creation failed: %s", e)
        raise

    # 2. Chatbot init (Ollama + Chroma)
    try:
        init_chatbot(engine)
        logger.info("✅ Chatbot initialized")
    except Exception as e:
        logger.exception("❌ Chatbot init failed — /chat will return 500")

    # 3. Pre-warm Ollama so the first real query doesn't wait 5+ minutes
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_CHAT_MODEL", "mistral")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            await client.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                    "keep_alive": "24h",
                },
            )
        logger.info("✅ Ollama model '%s' warmed up and pinned for 24h", model)
    except Exception as e:
        logger.warning("⚠️ Ollama warm-up failed (model may still load on first request): %s", e)


@app.get("/")
async def root():
    return {"message": "🤠 Student Performance Admin API is running!"}


@app.get("/health")
async def health():
    return {"status": "ok"}