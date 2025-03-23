from starlette.staticfiles import StaticFiles
from fastapi import HTTPException

from app.indicator import fetch_and_store_financial_data
from app.models import TextRequest
from app.services import save_generated_text, get_openai_response
from app.database import database

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.services import get_openai_response


app = FastAPI()


@app.get("/status")
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

""" --------------------------------front_end--------------------------------------"""

templates = Jinja2Templates(directory="templates")  # HTML 파일이 들어갈 폴더 지정
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def chatbot_page(request: Request):
    """ 챗봇 UI 페이지 제공 """
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/chat/")
async def chat(request: Request):
    """ 챗봇 API: 사용자의 입력을 받아 OpenAI에서 응답 생성 후 반환 """
    if request.method != "POST":
        raise HTTPException(status_code=405, detail="This endpoint only accepts POST requests.")

    form = await request.form()
    user_input = form["prompt"]

    response_text = await get_openai_response(user_input)  # OpenAI API 호출
    await save_generated_text(user_input, response_text)

    return HTMLResponse(f'<div class="message bot">{response_text}</div>')

