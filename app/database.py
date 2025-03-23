from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGO_URI

# MongoDB 클라이언트 생성
client = AsyncIOMotorClient(MONGO_URI)
database = client["financeai"]  # ← 이거 확실하게 DB 지정

# ✅ OpenAI 응답 컬렉션
generated_texts_collection = database.get_collection("generated_texts")

# ✅ 금융 데이터 컬렉션
financial_data_collection = database.get_collection("financial_data")



