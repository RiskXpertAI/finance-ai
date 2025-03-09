from fastapi import FastAPI
from app.models import TextRequest
from app.services import generate_text, save_generated_text
from app.database import database

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "MongoDB 연결 성공!"}

@app.post("/generate_text/")
async def generate_text_and_save(request: TextRequest):
    collection = database.get_collection("generated_texts")  # collection 가져오기
    generated_text = await generate_text(request.prompt)
    await save_generated_text(request.prompt, generated_text)
    return {"generated_text": generated_text}
