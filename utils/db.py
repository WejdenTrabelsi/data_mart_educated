import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def get_source_engine():
    server = os.getenv('SOURCE_SERVER')
    db = os.getenv('SOURCE_DB')
    
    # Stronger connection string for Arabic support
    conn_str = (
        f"mssql+pyodbc://{server}/{db}?"
        f"driver=ODBC+Driver+17+for+SQL+Server&"
        f"Trusted_Connection=yes&"
        f"charset=utf8&"
        f"autocommit=true&"
        f"Encrypt=no"
    )
    return create_engine(conn_str, fast_executemany=True, echo=False)

def get_warehouse_engine():
    server = os.getenv('WAREHOUSE_SERVER')
    db = os.getenv('WAREHOUSE_DB')
    
    conn_str = (
        f"mssql+pyodbc://{server}/{db}?"
        f"driver=ODBC+Driver+17+for+SQL+Server&"
        f"Trusted_Connection=yes&"
        f"charset=utf8"
    )
    return create_engine(conn_str, fast_executemany=True)