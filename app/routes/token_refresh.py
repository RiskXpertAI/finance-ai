from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.tokens import decode_token, create_access_token
import jwt

router = APIRouter()
security = HTTPBearer()


@router.post("/token/refresh")
def refresh_access_token(token: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = decode_token(token.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid refresh token")

        new_access_token = create_access_token({"sub": user_id})
        return {"access_token": new_access_token}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")