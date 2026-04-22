from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "Users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)
    status = Column(String(20), default="approved")           # NEW
    student_natural_key = Column(String(50), nullable=True)
    remarks = Column(String(500), nullable=True)   # NEW
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime, nullable=True)
    