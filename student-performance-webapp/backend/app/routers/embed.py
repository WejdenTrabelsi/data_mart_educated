from fastapi import APIRouter, Depends
from jose import jwt
import time
from ..core.config import settings
from ..routers.auth import get_current_user
from ..models.user import User

router = APIRouter(prefix="/embed", tags=["embed"])

DASHBOARD_ID = 3   # ← your real ID

@router.get("/dashboard")
async def get_signed_dashboard(current_user: User = Depends(get_current_user)):
    now = int(time.time())
    payload = {
        "resource": {"dashboard": DASHBOARD_ID},
        "params": {},
        "iat": now,                    # ← added (issued at)
        "exp": now + 3600              # 1 hour
    }
    
    token = jwt.encode(payload, settings.METABASE_SECRET_KEY, algorithm="HS256")
    
    embed_url = f"{settings.METABASE_SITE_URL}/embed/dashboard/{DASHBOARD_ID}?jwt={token}"
    return {"embed_url": embed_url}