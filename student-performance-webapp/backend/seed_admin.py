from app.database import engine, SessionLocal
from app.models.user import User, Base
from app.core.security import get_password_hash

# 🔥 Force-recreate the Users table to match the new model (no role/status columns)
print("Resetting Users table to match new schema...")
Base.metadata.drop_all(bind=engine, tables=[User.__table__])
Base.metadata.create_all(bind=engine, tables=[User.__table__])
print("Users table recreated.")

db = SessionLocal()

existing = db.query(User).filter(User.username == "admin").first()
if existing:
    print("Admin user already exists.")
else:
    admin = User(
        username="admin",
        email="admin@lycee.tn",
        password_hash=get_password_hash("admin123"),
        full_name="Administrateur"
    )
    db.add(admin)
    db.commit()
    print("✅ Admin user created: username=admin | password=admin123")

db.close()