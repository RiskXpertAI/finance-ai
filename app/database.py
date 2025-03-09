from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGO_URI

# MongoDB 클라이언트 생성
client = AsyncIOMotorClient(MONGO_URI)
database = client.financeai  # 기본 DB 선택

# ✅ OpenAI 응답 컬렉션
generated_texts_collection = database.get_collection("generated_texts")  # 저장할 컬렉션 이름

# ✅ 금융 데이터 컬렉션
financial_data_collection = database.get_collection("financial_data")
