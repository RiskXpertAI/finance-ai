import jwt
import datetime
import os
import logging
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = 1
REFRESH_TOKEN_EXPIRE_DAYS = 0.002  # 2분

# 예외 처리 + 로깅
if not SECRET_KEY:
    logging.warning("SECRET_KEY가 설정되지 않았습니다! `.env` 파일을 확인하세요!")

# Access Token 생성
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    logging.info("[Token] Access Token 생성 완료")
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")


# Refresh Token 생성
def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})

    logging.info("[Token] Refresh Token 생성 완료")
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")


# Token 디코딩
def decode_token(token: str):
    logging.info("[Token] Token 디코딩 시도")
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])