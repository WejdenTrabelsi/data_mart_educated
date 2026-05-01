# ---------------------------------------------------------------------------
# DATABASE.PY  --  SQLAlchemy Engine & Session Factory
# ---------------------------------------------------------------------------
# This file creates the "bridge" between Python and SQL Server.
# It defines:
#   1. engine        -- the low-level connection pool
#   2. SessionLocal  -- a factory that creates new database sessions
#   3. get_db()      -- a FastAPI dependency that yields sessions safely
# ---------------------------------------------------------------------------

# create_engine builds the connection pool to the database.
from sqlalchemy import create_engine

# sessionmaker creates configurable Session factories.
from sqlalchemy.orm import sessionmaker

# Our settings object that holds the ODBC connection string.
from .core.config import settings

# ---------------------------------------------------------------------------
# engine is the "mother" connection. It knows the server address, driver,
# and credentials. SQLAlchemy keeps a pool of connections inside it so
# requests do not open a brand-new TCP connection every time.
# ---------------------------------------------------------------------------
# The connection string format is:
#   mssql+pyodbc:///?odbc_connect=<URL-encoded ODBC string>
# The +pyodbc part tells SQLAlchemy to use the pyodbc driver under the hood.
# echo=False disables SQL logging; set to True to see every query in console.
# ---------------------------------------------------------------------------
engine = create_engine(
    f"mssql+pyodbc:///?odbc_connect={settings.DATABASE_URL}",
    echo=False
)

# ---------------------------------------------------------------------------
# SessionLocal is a factory class. Every time we call SessionLocal(), we get
# a new Session object that represents one database transaction.
# autocommit=False means we must manually call db.commit() to save changes.
# autoflush=False delays sending SQL to the server until we explicitly ask.
# bind=engine ties this session factory to our SQL Server engine.
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# get_db()  --  FastAPI Dependency
# ---------------------------------------------------------------------------
# FastAPI calls this function automatically whenever a route declares
# db: Session = Depends(get_db).
# The "yield" keyword turns this into a generator: it hands the session
# to the endpoint, pauses, and resumes afterward to close the session.
# The "finally" block guarantees the session closes even if the endpoint
# crashes with an unhandled exception.
# ---------------------------------------------------------------------------
def get_db():
    # Open a new session from the pool.
    db = SessionLocal()
    try:
        # Yield pauses here and passes db to the endpoint function.
        yield db
    finally:
        # This runs AFTER the endpoint finishes, success or failure.
        # Closing returns the connection to the pool so it can be reused.
        db.close()