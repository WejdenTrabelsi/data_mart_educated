import os
os.environ["PYTHONUTF8"] = "1"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.auth import router as auth_router
from .routers.dashboard import router as dashboard_router  # NEW
from .models.user import Base
from .database import engine

from .chatbot import router as chatbot_router, init_chatbot

app = FastAPI(
    title="Student Performance API",
    description="Backend for Admin Dashboard",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dashboard_router)  # NEW - replaces embed_router
app.include_router(chatbot_router)

@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    init_chatbot(engine)

@app.get("/")
async def root():
    return {"message": "✅ Student Performance Admin API is running!"}