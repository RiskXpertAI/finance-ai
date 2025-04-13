import os
from dotenv import load_dotenv, find_dotenv

# .env 파일 경로 찾기
env_path = find_dotenv()
if not env_path:
    print("🚨 `.env` 파일을 찾을 수 없습니다! 프로젝트 루트에 있는지 확인하세요!")
else:
    print(f"✅ `.env` 파일 경로: {env_path}")

# .env 파일 로드
load_dotenv()

# 환경 변수 불러오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
REDIS_URL = os.getenv("REDIS_URL")
PREDICT_API_URL = os.getenv("PREDICT_API_URL")
# 값이 제대로 불러와졌는지 확인
print(f"🔍 OPENAI_API_KEY loaded successful")  # 값이 출력되는지 확인
print(f"🔍 MONGO_URI: {MONGO_URI}")  # 값이 출력되는지 확인

# API 키가 없으면 경고 메시지 출력
if not OPENAI_API_KEY:
    print("🚨 OpenAI API 키가 설정되지 않았습니다! `.env` 파일을 확인하세요!")

