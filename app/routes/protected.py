# app/routes/protected.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt, os
from dotenv import load_dotenv
from app.tokens import decode_token, create_access_token

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your_jwt_secret")
router = APIRouter()
security = HTTPBearer()

# 🔐 JWT 검증
def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ✅ 인증된 유저 확인용 API
@router.get("/me")
def read_protected_route(user: dict = Depends(get_current_user)):
    return {"message": "✅ 인증 성공", "user_id": user.get("sub")}

# ♻️ 토큰 갱신
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