# ---------------------------------------------------------------------------
# SEED_ADMIN.PY  --  Database Seeding Script
# ---------------------------------------------------------------------------
# Run this script ONCE (or whenever you reset the Users table) to create
# the default administrator account. It deletes and recreates the Users
# table, then inserts one admin user with a hashed password.
# ---------------------------------------------------------------------------

# engine is the SQLAlchemy connection pool.
# SessionLocal creates new database sessions.
from app.database import engine, SessionLocal

# User is the ORM model; Base gives us metadata access.
from app.models.user import User, Base

# get_password_hash turns "admin123" into a secure bcrypt hash.
from app.core.security import get_password_hash

# ---------------------------------------------------------------------------
# WARNING: drop_all DESTROYS the existing Users table and all its data.
# This ensures the table schema matches the current User model exactly.
# In production you would use Alembic migrations instead of drop_all.
# ---------------------------------------------------------------------------
print("Resetting Users table to match new schema...")
Base.metadata.drop_all(bind=engine, tables=[User.__table__])
Base.metadata.create_all(bind=engine, tables=[User.__table__])
print("Users table recreated.")

# ---------------------------------------------------------------------------
# Open a manual session. Unlike get_db(), this is not a generator,
# so we must remember to close it ourselves at the end.
# ---------------------------------------------------------------------------
db = SessionLocal()

# ---------------------------------------------------------------------------
# Check if an admin already exists to avoid duplicates.
# -----------------------------------------------------------------------
existing = db.query(User).filter(User.username == "admin").first()
if existing:
    print("Admin user already exists.")
else:
    # Build the admin user object.
    # password_hash receives the BCRYPT hash, NOT the plain text.
    admin = User(
        username="admin",
        email="admin@lycee.tn",
        password_hash=get_password_hash("admin123"),
        full_name="Administrateur"
    )
    
    # Stage the new row for insertion.
    db.add(admin)
    
    # Actually commit the INSERT statement to SQL Server.
    db.commit()
    
    print("✅ Admin user created: username=admin | password=admin123")

# Always close the session to return the connection to the pool.
db.close()