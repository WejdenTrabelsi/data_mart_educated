# This file creates the "bridge" between Python and SQL Server.
# It defines:
#   1. engine        -- the low-level connection pool
#   2. SessionLocal  -- a factory that creates new database sessions
#   3. get_db()      -- a FastAPI dependency that yields sessions safely


# create_engine builds the connection pool to the database.
from sqlalchemy import create_engine

# sessionmaker creates configurable Session factories.
from sqlalchemy.orm import sessionmaker

# we only need the DATABASE_URL from it 
from .core.config import settings


# SQLAlchemy keeps a pool of connections inside it so requests do not open a brand-new TCP connection every time.
# The connection string format is:
#   mssql+pyodbc:///?odbc_connect=<URL-encoded ODBC string>

engine = create_engine( #create_engine returns a special Engine object
    f"mssql+pyodbc:///?odbc_connect={settings.DATABASE_URL}",
    echo=False #disable sql logging if true every sql query will print in terminal !
) #mssql means i am speaking to microsoft sql server 
#+pyodbc means use the pyodbc python library as the messenger

"""What is a connection pool?
 When the first request hits your API, create_engine opens a TCP connection to SQL Server. 
 Instead of closing it after the query, it keeps it open in a "pool." 
 The next request reuses that same physical connection. 
 This avoids the ~50ms overhead of handshaking every time. 
 SQLAlchemy manages this automatically."""




# SessionLocal is a factory class. Every time we call SessionLocal(), we get
# a new Session object that represents one database transaction.
# autocommit=False means we must manually call db.commit() to save changes.
# autoflush=False delays sending SQL to the server until we explicitly ask.
# bind=engine ties this session factory to our SQL Server engine.

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)




# FastAPI calls this function automatically whenever a route declares
# db: Session = Depends(get_db).
# "yeild" turns a function inti a generator 
"""what happens ?
FastAPI calls get_db()
db=SessionLocal() runs
yield db pauses the function and hands db to our API endpoint
our endpoint runs its SQL queries using db
when endpoint finishes (returns JSON) FastAPI resumes get_db() right after yield
"""

# The "finally" block guarantees the session closes even if the endpoint
# crashes with an unhandled exception.

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