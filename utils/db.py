import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def get_source_engine():
    """Connection to raw database: educated-bd-2"""
    server = os.getenv('SOURCE_SERVER')
    db = os.getenv('SOURCE_DB')
    driver = os.getenv('SOURCE_DRIVER', 'ODBC Driver 17 for SQL Server')
    trusted = os.getenv('SOURCE_TRUSTED_CONNECTION', 'yes')

    conn_str = (
        f"mssql+pyodbc://{server}/{db}?"
        f"driver={driver.replace(' ', '+')}&"
        f"Trusted_Connection={trusted}"
    )
    return create_engine(conn_str, fast_executemany=True)

def get_warehouse_engine():
    """Connection to the star schema database"""
    server = os.getenv('WAREHOUSE_SERVER')
    db = os.getenv('WAREHOUSE_DB')
    driver = os.getenv('WAREHOUSE_DRIVER', 'ODBC Driver 17 for SQL Server')
    trusted = os.getenv('WAREHOUSE_TRUSTED_CONNECTION', 'yes')

    conn_str = (
        f"mssql+pyodbc://{server}/{db}?"
        f"driver={driver.replace(' ', '+')}&"
        f"Trusted_Connection={trusted}"
    )
    return create_engine(conn_str, fast_executemany=True)