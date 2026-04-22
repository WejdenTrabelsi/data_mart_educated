from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .core.config import settings

engine = create_engine(
    f"mssql+pyodbc:///?odbc_connect={settings.DATABASE_URL}",
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()