from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
    
    # NEW — Metabase signed embed
    METABASE_SECRET_KEY: str = os.getenv("METABASE_SECRET_KEY")
    METABASE_SITE_URL: str = os.getenv("METABASE_SITE_URL", "http://localhost:3000")

settings = Settings()