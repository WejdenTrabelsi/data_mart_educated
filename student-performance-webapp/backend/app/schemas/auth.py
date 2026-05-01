# ---------------------------------------------------------------------------
# SCHEMAS/AUTH.PY  --  Data Shapes (Pydantic Models)
# ---------------------------------------------------------------------------
# Schemas are "contracts" that describe what data should look like.
# FastAPI uses them to:
#   - Validate incoming JSON/form data automatically
#   - Document the API in the interactive Swagger UI
#   - Serialize outgoing data so Python objects become clean JSON
# ---------------------------------------------------------------------------

# BaseModel is the core of Pydantic. Every schema inherits from it.
from pydantic import BaseModel

# Optional lets us declare that a field may be None.
from typing import Optional


# ---------------------------------------------------------------------------
# Token  --  What the backend returns after a successful login
# ---------------------------------------------------------------------------
class Token(BaseModel):
    # The actual JWT string (long, encoded, signed).
    access_token: str
    
    # Always "bearer" for OAuth2 password flows. Tells clients how to use it.
    token_type: str
    
    # The user's display name so the frontend can greet them immediately
    # without making a second API call.
    full_name: str


# ---------------------------------------------------------------------------
# TokenData  --  Internal representation of what we store inside a JWT
# ---------------------------------------------------------------------------
class TokenData(BaseModel):
    # The username extracted from the "sub" claim.
    # Optional because during validation we might not have it yet.
    username: Optional[str] = None


# ---------------------------------------------------------------------------
# UserLogin  --  Optional schema for raw JSON login (not used by OAuth2 form)
# ---------------------------------------------------------------------------
class UserLogin(BaseModel):
    # The login identifier typed by the user.
    username: str
    
    # The plain text password. It is NOT stored; only used for verification.
    password: str