from fastapi import FastAPI

from app.indicator import fetch_and_store_financial_data
from app.models import TextRequest
from app.services import save_generated_text, get_openai_response
from app.database import database

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "MongoDB 연결 성공!"}

@app.post("/generate_text/")
async def generate_text_and_save(request: TextRequest):
    collection = database.get_collection("generated_texts")  # collection 가져오기

    print(f"🔵 OpenAI API 요청을 보냅니다: {request.prompt}")  # 요청 로그 확인용 print 추가
    generated_text = await get_openai_response(request.prompt)  # OpenAI API 호출
    print(f"🟢 OpenAI API 응답 받음: {generated_text}")  # 응답 확인

    await save_generated_text(request.prompt, generated_text)  # MongoDB 저장
    return {"generated_text": generated_text}

# ✅ 금융 데이터 수집 및 저장 API
@app.post("/fetch-financial-data/")
async def fetch_financial_data():
    """ 한국은행 API에서 금융 데이터를 가져와 MongoDB에 저장하는 API """
    response = await fetch_and_store_financial_data()
    return response

