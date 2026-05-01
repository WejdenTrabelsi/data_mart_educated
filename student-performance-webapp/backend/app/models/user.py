# ---------------------------------------------------------------------------
# MODELS/USER.PY  --  SQL Table Blueprint (ORM Model)
# ---------------------------------------------------------------------------
# This file defines what the "Users" table looks like in SQL Server.
# Instead of writing raw SQL CREATE TABLE statements, we write a Python class.
# SQLAlchemy translates this class into SQL automatically.
# ---------------------------------------------------------------------------

# Column      = represents one column in the table
# Integer     = SQL INT
# String      = SQL VARCHAR
# DateTime    = SQL DATETIME
from sqlalchemy import Column, Integer, String, DateTime

# func gives us database functions like NOW() / GETDATE()
from sqlalchemy.sql import func

# declarative_base is the factory that creates the base class all models
# must inherit from. It connects the Python class to SQLAlchemy machinery.
from sqlalchemy.orm import declarative_base

# ---------------------------------------------------------------------------
# Base is the "root" object. Every table in your app should inherit from it.
# It stores metadata (table names, columns, relationships) that SQLAlchemy
# uses to generate SQL queries and create tables.
# ---------------------------------------------------------------------------
Base = declarative_base()

# ---------------------------------------------------------------------------
# The User class maps 1-to-1 to a table named "Users" in SQL Server.
# Each attribute becomes a column. Each instance of this class represents
# one row from the database.
# ---------------------------------------------------------------------------
class User(Base):
    # __tablename__ tells SQLAlchemy exactly what the SQL table is called.
    __tablename__ = "Users"
    
    # user_id is the PRIMARY KEY. It uniquely identifies every user.
    # primary_key=True adds the PRIMARY KEY constraint.
    # index=True creates a database index for faster lookups by ID.
    user_id = Column(Integer, primary_key=True, index=True)
    
    # username stores the login name.
    # String(50) means VARCHAR(50) in SQL.
    # unique=True prevents two users from having the same username.
    # nullable=False means this column cannot be empty.
    username = Column(String(50), unique=True, index=True, nullable=False)
    
    # email stores the user's email address with the same constraints.
    email = Column(String(100), unique=True, index=True, nullable=False)
    
    # password_hash stores the bcrypt-scrambled password.
    # It is never the plain text password — that would be a security disaster.
    password_hash = Column(String(255), nullable=False)
    
    # full_name is the display name shown in the frontend Navbar.
    full_name = Column(String(100), nullable=False)
    
    # created_at automatically records when the account was created.
    # func.now() translates to SQL Server's GETDATE() at insert time.
    created_at = Column(DateTime, default=func.now())
    
    # last_login records the most recent successful login.
    # nullable=True allows it to be NULL before the first login ever happens.
    last_login = Column(DateTime, nullable=True)