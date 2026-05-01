# ---------------------------------------------------------------------------
# SECURITY.PY  --  Password Hashing & JWT Token Factory
# ---------------------------------------------------------------------------
# This file handles everything sensitive: scrambling passwords so they are
# unreadable, checking if a typed password matches the scrambled version,
# and creating the signed "session passes" (JWT tokens) that the frontend
# stores after login.
# ---------------------------------------------------------------------------

# datetime gives us the current time; timedelta lets us add hours/minutes.
from datetime import datetime, timedelta

# jose (JavaScript Object Signing and Encryption) is the library that
# encodes/decodes JWT tokens. JWTError is raised when a token is invalid.
from jose import JWTError, jwt

# bcrypt is a password-hashing algorithm designed to be slow on purpose.
# Slowness makes brute-force attacks (trying millions of passwords) harder.
import bcrypt

# We import our central config so we can read SECRET_KEY and ALGORITHM.
from .config import settings


# ---------------------------------------------------------------------------
# verify_password()
# ---------------------------------------------------------------------------
# Called during login. Takes the plain text password the user typed
# and the hashed password stored in the database, then checks if they match.
# ---------------------------------------------------------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt.checkpw needs bytes, not strings, so we encode both to UTF-8.
    # UTF-8 is the standard text encoding that covers almost all characters.
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


# ---------------------------------------------------------------------------
# get_password_hash()
# ---------------------------------------------------------------------------
# Called when creating a new user (e.g., seed_admin.py).
# It turns a readable password into an irreversible scrambled hash.
# ---------------------------------------------------------------------------
def get_password_hash(password: str) -> str:
    # bcrypt.gensalt() creates a random "salt" — extra noise added to the
    # password before hashing. This ensures two identical passwords produce
    # completely different hashes, preventing rainbow-table attacks.
    salt = bcrypt.gensalt()
    
    # hashpw combines the password bytes with the salt and runs the slow
    # bcrypt algorithm to produce the final hash.
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    
    # We decode the resulting bytes back to a string so SQLAlchemy can
    # store it in the VARCHAR column of the database.
    return hashed.decode("utf-8")


# ---------------------------------------------------------------------------
# create_access_token()
# ---------------------------------------------------------------------------
# Called after successful login. Builds a JWT that proves the user's identity
# for the next 24 hours (or whatever ACCESS_TOKEN_EXPIRE_MINUTES says).
# ---------------------------------------------------------------------------
def create_access_token(data: dict):
    # We copy the input dictionary so we do not accidentally mutate the
    # caller's original data. This is defensive programming.
    to_encode = data.copy()
    
    # datetime.utcnow() gives the current time in Coordinated Universal Time.
    # timedelta(minutes=...) adds the configured expiration duration.
    # The result is the exact moment when this token should stop working.
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # We inject the expiration claim ("exp") into the dictionary.
    # JWT standards reserve "exp" — libraries automatically reject expired tokens.
    to_encode.update({"exp": expire})
    
    # jwt.encode() turns the dictionary into a compact Base64Url string.
    # It uses SECRET_KEY as the signature key and HS256 as the algorithm.
    # If an attacker changes even one character of the token, the signature
    # becomes invalid and the backend will reject it.
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)