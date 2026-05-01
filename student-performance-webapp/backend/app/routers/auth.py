# ---------------------------------------------------------------------------
# ROUTERS/AUTH.PY  --  Authentication Endpoints (Login & Token Check)
# ---------------------------------------------------------------------------
# This file defines the URL routes under /auth.
# The two main jobs are:
#   1. POST /auth/login   → verify credentials and hand out a JWT
#   2. get_current_user   → verify a JWT and return the user object
# ---------------------------------------------------------------------------

# APIRouter lets us split routes into separate files instead of dumping
# everything into one giant main.py.
from fastapi import APIRouter, Depends, HTTPException, status

# OAuth2PasswordBearer tells FastAPI we expect a "Bearer <token>" header.
# OAuth2PasswordRequestForm parses the username/password form submission.
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

# func.now() gives the current database timestamp for last_login updates.
from sqlalchemy.sql import func

# Session is the SQLAlchemy handle for talking to the database.
from sqlalchemy.orm import Session

# jwt and JWTError are from python-jose; used to decode incoming tokens.
from jose import jwt, JWTError

# get_db() is our dependency that opens and closes database sessions.
from ..database import get_db

# The User ORM model lets us query the Users table.
from ..models.user import User

# Pydantic schemas enforce the shape of request/response data.
from ..schemas.auth import Token, TokenData

# Our homemade security utilities: password check and token creation.
from ..core.security import verify_password, create_access_token

# Central settings (SECRET_KEY, ALGORITHM, etc.)
from ..core.config import settings

# ---------------------------------------------------------------------------
# Create a router object. All routes in this file will be prefixed with /auth.
# tags=["auth"] groups these routes under "auth" in the auto-generated docs.
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# oauth2_scheme is a callable that FastAPI uses to extract the token from
# the Authorization header. tokenUrl="auth/login" tells the docs where to
# obtain a token. It does NOT perform validation by itself.
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ---------------------------------------------------------------------------
# get_current_user()  --  Reusable Token Verifier
# ---------------------------------------------------------------------------
# This is a FastAPI "dependency". Any protected endpoint can declare:
#     user: User = Depends(get_current_user)
# and FastAPI will automatically run this function first.
# ---------------------------------------------------------------------------
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    
    # We prepare a standardized 401 error. Including the Bearer header
    # tells HTTP clients this is an OAuth2-style authentication failure.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # -----------------------------------------------------------------------
    # Try to decode the JWT. If the token is expired, tampered with, or
    # malformed, jwt.decode() will raise JWTError and we immediately abort.
    # -----------------------------------------------------------------------
    try:
        # Decode using our secret key and the same algorithm that signed it.
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # The "sub" (subject) claim holds the username we embedded at login.
        username: str = payload.get("sub")
        
        # If there is no subject, the token is structurally invalid.
        if username is None:
            raise credentials_exception
        
        # Wrap the username in our Pydantic schema for type safety.
        token_data = TokenData(username=username)
    
    # Any problem with the token (expired, bad signature, bad format) → 401.
    except JWTError:
        raise credentials_exception

    # -----------------------------------------------------------------------
    # Token is valid, so we fetch the actual user row from SQL Server.
    # If the user was deleted after the token was issued, we also reject.
    # -----------------------------------------------------------------------
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    
    # Return the full User ORM object so the endpoint knows WHO is calling.
    return user


# ---------------------------------------------------------------------------
# POST /auth/login  --  The Actual Login Endpoint
# ---------------------------------------------------------------------------
# This is what the frontend calls when the Director clicks "Se connecter".
# response_model=Token guarantees the output matches our Token schema.
# ---------------------------------------------------------------------------
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    
    # -----------------------------------------------------------------------
    # Step 1: Find the user by username.
    # SQLAlchemy generates: SELECT * FROM Users WHERE username = ?
    # .first() returns either a User object or None.
    # -----------------------------------------------------------------------
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # -----------------------------------------------------------------------
    # Step 2: Verify credentials.
    # If the user does not exist OR the password does not match the hash,
    # we return 401 Unauthorized. We deliberately do NOT reveal whether
    # the username or the password was wrong — this prevents user enumeration.
    # -----------------------------------------------------------------------
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    
    # -----------------------------------------------------------------------
    # Step 3: Update last_login timestamp.
    # func.now() asks SQL Server for the current time.
    # db.commit() actually writes the change to disk.
    # -----------------------------------------------------------------------
    user.last_login = func.now()
    db.commit()
    
    # -----------------------------------------------------------------------
    # Step 4: Create the JWT access token.
    # The "sub" claim is standard for storing the subject's identity.
    # We embed the username so later requests can identify this user.
    # -----------------------------------------------------------------------
    access_token = create_access_token(data={"sub": user.username})
    
    # -----------------------------------------------------------------------
    # Step 5: Return the token bundle to the frontend.
    # The frontend extracts access_token and full_name and stores them.
    # -----------------------------------------------------------------------
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "full_name": user.full_name
    }