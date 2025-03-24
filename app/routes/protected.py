# app/routes/protected.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os
from dotenv import load_dotenv

from app.tokens import decode_token

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your_jwt_secret")
router = APIRouter()
security = HTTPBearer()

# ✅ JWT 검증 함수
def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    print(f"🧪 받은 토큰: {token.credentials}")
    print(f"✅ SECRET_KEY: {SECRET_KEY}")

    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=["HS256"])
        print(f"🟢 디코딩 성공! payload: {payload}")
        return payload
    except jwt.ExpiredSignatureError:
        print("❌ JWT Expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        print(f"❌ InvalidTokenError: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")

# ✅ 보호된 라우트
@router.get("/me")
def read_protected_route(user: dict = Depends(get_current_user)):
    return {"message": "✅ 인증 성공", "user_id": user.get("sub")}