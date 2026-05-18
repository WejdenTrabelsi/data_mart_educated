#schemas/auth.py is the API contract(what the HTTP request/response expects).
# FastAPI uses them to:
# +Validate incoming JSON/form data automatically
# +Document the API in the interactive Swagger UI
# +Serialize outgoing data so Python objects become clean JSON

#pydantic: The data-validation library. FastAPI is built on top of it.
# BaseModel is the parent class. Every schema inherits from it.
from pydantic import BaseModel # BaseModelgives auto type checking json serialization swagger ui generattion n error msg when validation fails

# Optional lets us declare that a field may be None. (3ibara string | null)
from typing import Optional


# What the backend returns after a successful login
#Token is the schema name it describes what /auth/login returns
class Token(BaseModel):
    # The actual JWT string (long, encoded, signed).
    access_token: str
    
    # Always "bearer" for OAuth2 password flows. Tells clients how to use it.
    token_type: str
    
    # The user's display name so the frontend can greet them immediately
    # without making a second API call.
    full_name: str


#TokenData is an internal schema front never sees it. it's only used inside 
#get_current_user to hold the username extracted from the JWT playload
class TokenData(BaseModel):
    # The username extracted from the "sub" claim.
    # Optional because during validation we might not have it yet.
    username: Optional[str] = None

"""i mean we could just do username = payload.get("sub")
but it's more for type safety (for example if we later change the token to hold roles permissions
we change just TokenData instead of every function that used the raw string)
 """

