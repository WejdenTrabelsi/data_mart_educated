import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

from pathlib import Path 
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"

load_dotenv(dotenv_path=env_path, override=True)
def get_source_engine(): 
    server = os.getenv('SOURCE_SERVER') 
    db = os.getenv('SOURCE_DB') 
    if not server or not db: 
        raise ValueError("Missing environment variables for SQL connection")
    user = os.getenv('SOURCE_USER')
    password = os.getenv('SOURCE_PASSWORD')

    conn_str = (
        f"mssql+pyodbc://{user}:{password}@{server}/{db}?"
        "driver=ODBC+Driver+17+for+SQL+Server&"
        "Encrypt=no"
    )

    return create_engine(conn_str, fast_executemany=True)


def get_warehouse_engine():
    server = os.getenv('WAREHOUSE_SERVER')
    db = os.getenv('WAREHOUSE_DB')
    user = os.getenv('WAREHOUSE_USER')
    password = os.getenv('WAREHOUSE_PASSWORD')

    if not all([server, db, user, password]):
        raise ValueError(
            f"Missing warehouse env vars: "
            f"server={server}, db={db}, user={user}, password={'SET' if password else 'MISSING'}"
        )

    conn_str = (
        f"mssql+pyodbc://{user}:{password}@{server}/{db}?"
        "driver=ODBC+Driver+17+for+SQL+Server&"
        "Encrypt=no"
    )

    return create_engine(conn_str, fast_executemany=True)