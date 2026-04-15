import os
from sqlalchemy import create_engine, event
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()

def get_source_engine():
    server = os.getenv('SOURCE_SERVER')
    db = os.getenv('SOURCE_DB')
    
    conn_str = (
        f"mssql+pyodbc://{server}/{db}?"
        f"driver=ODBC+Driver+17+for+SQL+Server&"
        f"Trusted_Connection=yes&"
        f"Encrypt=no&"
        f"autocommit=true"
        # ← charset=utf8 removed — invalid for SQL Server, causes ???
    )
    engine = create_engine(conn_str, fast_executemany=True, echo=False)
    return engine

def get_warehouse_engine():
    server = os.getenv('WAREHOUSE_SERVER')
    db = os.getenv('WAREHOUSE_DB')
    
    conn_str = (
        f"mssql+pyodbc://{server}/{db}?"
        f"driver=ODBC+Driver+17+for+SQL+Server&"
        f"Trusted_Connection=yes&"
        f"Encrypt=no"
        # ← charset=utf8 removed here too
    )
    engine = create_engine(conn_str, fast_executemany=True)
    return engine