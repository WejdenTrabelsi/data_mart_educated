from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..core.security import get_password_hash
from ..routers.auth import get_current_user   # ← THIS WAS MISSING
from pydantic import BaseModel

router = APIRouter(prefix="/parent", tags=["parent"])

class ParentRegister(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    student_natural_key: str
    level_name: str
    branch_name: str

class ApproveRequest(BaseModel):
    remarks: str = ""

@router.get("/levels")
async def get_levels(db: Session = Depends(get_db)):
    levels = db.execute("SELECT level_name FROM DimLevel ORDER BY level_name").fetchall()
    return [row[0] for row in levels]

@router.get("/branches")
async def get_branches(db: Session = Depends(get_db)):
    branches = db.execute("SELECT branch_name FROM DimBranch ORDER BY branch_name").fetchall()
    return [row[0] for row in branches]

@router.post("/register")
async def register_parent(data: ParentRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "Username already taken")
    
    new_user = User(
        username=data.username,
        email=data.email,
        password_hash=get_password_hash(data.password),
        full_name=data.full_name,
        role="parent",
        status="pending",
        student_natural_key=data.student_natural_key,
    )
    db.add(new_user)
    db.commit()
    return {"message": "Demande envoyée. En attente d'approbation."}

@router.get("/pending")
async def get_pending_parents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "director":
        raise HTTPException(403, "Only director")
    parents = db.query(User).filter(User.status == "pending").all()
    return parents

@router.post("/approve/{user_id}")
async def approve_parent(user_id: int, req: ApproveRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "director":
        raise HTTPException(403, "Only director")
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        user.status = "approved"
        user.remarks = req.remarks
        db.commit()
    return {"message": "Parent approved"}