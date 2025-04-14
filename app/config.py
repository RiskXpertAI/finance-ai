import os
import logging
from dotenv import load_dotenv, find_dotenv

# .env 파일 경로 찾기
env_path = find_dotenv()
if not env_path:
    logging.warning("[.env] 파일 없음")

else:
    logging.info(f"✅ `.env` 파일 경로: {env_path}")

# .env 파일 로드
load_dotenv()

# 환경 변수 불러오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
REDIS_URL = os.getenv("REDIS_URL")
PREDICT_API_URL = os.getenv("PREDICT_API_URL")

# 로딩 성공 여부 로깅
logging.info("🔍 OPENAI_API_KEY loaded successful")
logging.info(f"🔍 MONGO_URI: {MONGO_URI}")

if not OPENAI_API_KEY:
    logging.warning("🚨 OpenAI API 키가 설정되지 않았습니다! `.env` 파일을 확인하세요!")