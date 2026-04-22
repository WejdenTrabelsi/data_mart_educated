import os
os.environ["PYTHONUTF8"] = "1"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.auth import router as auth_router
from .routers.embed import router as embed_router
from .routers.parent import router as parent_router
from .models.user import Base
from .database import engine

# NEW — chatbot
from .chatbot import router as chatbot_router, init_chatbot

app = FastAPI(
    title="Student Performance API",
    description="Backend for Director + Parents web app",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(embed_router)
app.include_router(parent_router)
app.include_router(chatbot_router)   # NEW

@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    init_chatbot(engine)             # NEW — pass your existing engine

@app.get("/")
async def root():
    return {"message": "✅ Student Performance Web App API is running!"}