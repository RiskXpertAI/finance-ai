from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGO_URI

# MongoDB 클라이언트 생성
client = AsyncIOMotorClient(MONGO_URI)
database = client.financeai  # 기본 DB 선택
collection = database.get_collection("generated_texts")  # 저장할 컬렉션 이름
