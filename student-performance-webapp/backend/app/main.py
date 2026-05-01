# ---------------------------------------------------------------------------
# MAIN.PY  --  Application Entry Point
# ---------------------------------------------------------------------------
# This is the file you run to start the server:
#     uvicorn app.main:app --reload
# It assembles all routers, middleware, and startup logic into one FastAPI app.
# ---------------------------------------------------------------------------

# Force Python to use UTF-8 mode so special characters (accents, etc.)
# are handled correctly on Windows.
import os
os.environ["PYTHONUTF8"] = "1"

# FastAPI is the web framework. It handles HTTP requests, routing, validation,
# automatic JSON parsing, and interactive documentation.
from fastapi import FastAPI

# CORS = Cross-Origin Resource Sharing.
# Browsers block frontend JavaScript from talking to a different origin
# (different port or domain) unless the server explicitly allows it.
from fastapi.middleware.cors import CORSMiddleware

# Import our route modules. Each router handles a slice of the API.
from .routers.auth import router as auth_router
from .routers.dashboard import router as dashboard_router  # NEW
from .models.user import Base
from .database import engine
from .routers import suggestions 
from .chatbot import router as chatbot_router, init_chatbot

# ---------------------------------------------------------------------------
# Create the FastAPI application instance.
# title, description, and version appear in the auto-generated docs at /docs.
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Student Performance API",
    description="Backend for Admin Dashboard",
    version="2.0.0"
)

# ---------------------------------------------------------------------------
# Add CORS middleware.
# allow_origins=["*"] means ANY website can call this API.
# In production you would restrict this to your exact frontend domain.
# allow_credentials=True lets cookies/auth headers pass through.
# allow_methods=["*"] and allow_headers=["*"] permit all HTTP verbs/headers.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Mount the routers.
# Each router brings its own URLs under its prefix.
# For example, auth_router provides /auth/login.
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(dashboard_router)  # NEW - replaces embed_router
app.include_router(chatbot_router)
app.include_router(suggestions.router)

# ---------------------------------------------------------------------------
# Startup Event
# ---------------------------------------------------------------------------
# @app.on_event("startup") registers a function that runs ONCE when the
# server boots up. We use it to:
#   1. Create SQL tables if they do not already exist (create_all).
#   2. Initialize the AI chatbot (load models, vector DB, etc.).
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    # Base.metadata.create_all looks at every class inheriting from Base
    # (like User) and issues CREATE TABLE IF NOT EXISTS statements.
    Base.metadata.create_all(bind=engine)
    
    # init_chatbot sets up the Ollama / ChromaDB components.
    init_chatbot(engine)

# ---------------------------------------------------------------------------
# Root Health-Check Endpoint
# ---------------------------------------------------------------------------
# Visiting GET / returns a friendly message confirming the server is alive.
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "✅ Student Performance Admin API is running!"}