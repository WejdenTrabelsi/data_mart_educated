import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from pathlib import Path 

BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path, override=True)


def _build_engine(server: str, db: str, user: str | None, password: str | None):
    """Construit la connection string selon le mode d'authentification disponible."""
    if not server or not db:
        raise ValueError(f"Missing server or database: server={server}, db={db}")

    # SQL Authentication (user + password fournis)
    if user and password:
        conn_str = (
            f"mssql+pyodbc://{user}:{password}@{server}/{db}?"
            "driver=ODBC+Driver+17+for+SQL+Server&"
            "Encrypt=no"
        )
    else:
        # Windows Authentication (Trusted Connection)
        conn_str = (
            f"mssql+pyodbc://@{server}/{db}?"
            "driver=ODBC+Driver+17+for+SQL+Server&"
            "Trusted_Connection=yes&"
            "Encrypt=no"
        )

    return create_engine(conn_str, fast_executemany=True)


def get_source_engine(): 
    server = os.getenv('SOURCE_SERVER') 
    db = os.getenv('SOURCE_DB')
    user = os.getenv('SOURCE_USER')
    password = os.getenv('SOURCE_PASSWORD')

    return _build_engine(server, db, user, password)


def get_warehouse_engine():
    server = os.getenv('WAREHOUSE_SERVER')
    db = os.getenv('WAREHOUSE_DB')
    user = os.getenv('WAREHOUSE_USER')
    password = os.getenv('WAREHOUSE_PASSWORD')

    return _build_engine(server, db, user, password)