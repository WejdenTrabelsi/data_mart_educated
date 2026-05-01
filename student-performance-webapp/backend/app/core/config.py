# ---------------------------------------------------------------------------
# CONFIG.PY  --  Central Configuration Hub
# ---------------------------------------------------------------------------
# This file is the "settings brain" of the entire backend.
# It reads secret values from the .env file and exposes them as a clean
# Python object that every other module can import safely.
# ---------------------------------------------------------------------------

# Pydantic Settings gives us automatic validation + type checking for env vars
from pydantic_settings import BaseSettings

# python-dotenv reads the .env file (key=value pairs) into environment variables
from dotenv import load_dotenv

# os allows us to read those environment variables
import os

# ---------------------------------------------------------------------------
# load_dotenv() looks for a file named .env in the current directory.
# It takes every line like SECRET_KEY=abc123 and puts it into the OS
# environment so os.getenv() can see it later.
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# We define a Settings class that inherits from BaseSettings.
# BaseSettings is special: it automatically maps class attributes to
# environment variables with the SAME NAME.
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    
    # DATABASE_URL holds the ODBC connection string used by SQLAlchemy.
    # os.getenv("DATABASE_URL") fetches the value from the .env file.
    # If .env is missing this key, it returns None (which would crash later).
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # SECRET_KEY is the cryptographic key used to SIGN every JWT token.
    # Anyone who knows this key can forge tokens, so it must stay secret.
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    
    # ALGORITHM tells the JWT library which signing method to use.
    # HS256 = HMAC with SHA-256. It is fast and widely supported.
    ALGORITHM: str = os.getenv("ALGORITHM")
    
    # ACCESS_TOKEN_EXPIRE_MINUTES controls how long a login session lasts.
    # The default value 1440 means 24 hours (60 * 24).
    # int() converts the string from .env into a real integer.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
    
    # -----------------------------------------------------------------------
    # The following two variables belong to the METABASE dashboard module.
    # They are NOT used by authentication but live here for convenience.
    # METABASE_SECRET_KEY is used to cryptographically sign embedded iframes.
    # -----------------------------------------------------------------------
    METABASE_SECRET_KEY: str = os.getenv("METABASE_SECRET_KEY")
    
    # METABASE_SITE_URL is the base address where Metabase is running.
    # The default fallback is localhost:3000 if .env omits it.
    METABASE_SITE_URL: str = os.getenv("METABASE_SITE_URL", "http://localhost:3000")

# ---------------------------------------------------------------------------
# We create exactly ONE instance of Settings and export it.
# This is called the Singleton pattern: every file imports the same object,
# so we never re-read .env multiple times.
# ---------------------------------------------------------------------------
settings = Settings()