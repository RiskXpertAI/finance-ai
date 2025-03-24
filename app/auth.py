# app/auth.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
import os, httpx
from dotenv import load_dotenv
from app.tokens import create_access_token, create_refresh_token
from urllib.parse import urlencode

load_dotenv()
router = APIRouter()

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")

@router.get("/login")
def login():
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?"
        f"client_id={KAKAO_CLIENT_ID}&redirect_uri={KAKAO_REDIRECT_URI}&response_type=code"
    )
    return RedirectResponse(kakao_auth_url)

@router.get("/login/callback")
async def kakao_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": KAKAO_CLIENT_ID,
                "redirect_uri": KAKAO_REDIRECT_URI,
                "code": code,
                "client_secret": KAKAO_CLIENT_SECRET,
            },
        )
        token_json = token_response.json()
        access_token_kakao = token_json.get("access_token")

        if not access_token_kakao:
            raise HTTPException(status_code=400, detail="카카오 토큰 발급 실패")

        user_info_response = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token_kakao}"},
        )
        user_info = user_info_response.json()
        kakao_id = user_info["id"]

        # ✅ JWT 토큰 생성
        access_token = create_access_token({"sub": str(kakao_id)})
        refresh_token = create_refresh_token({"sub": str(kakao_id)})

        # ✅ index 페이지로 토큰 포함한 리디렉션
        query_params = urlencode({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "kakao_id": kakao_id
        })
        return RedirectResponse(url=f"/?{query_params}")