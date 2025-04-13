import asyncio
import hashlib
import logging
from fastapi.responses import StreamingResponse

from openai import OpenAI
from pydantic import ValidationError
from starlette.staticfiles import StaticFiles

from app.indicator import fetch_and_store_financial_data
from app.models import TextRequest
from app.database import database

from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse


from fastapi import FastAPI, HTTPException, Form, Request
from app.services import get_openai_response, save_generated_text, build_forecast_prompt, get_scenario_based_answer
from app.redis_cache import cache_forecast, get_cached_forecast, call_prediction_api, get_redis_client
from app.transformer import run_forecasting, ChatRequest
from starlette.responses import JSONResponse
from app.routes import protected
from app.routes.auth import router as auth_router, KAKAO_CLIENT_ID, KAKAO_REDIRECT_URI  # 카카오 로그인 라우터

logging.basicConfig(level=logging.DEBUG)

app = FastAPI()
client=OpenAI()

# 카카오 로그인
app.include_router(auth_router)

# ✅ 보호된 라우터 등록
app.include_router(protected.router)

templates = Jinja2Templates(directory="templates")


@app.get("/health/mongo")
async def mongo_health_check():
    try:
        await database.command("ping")
        return {"status": "ok", "msg": "MongoDB connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health/redis")
async def redis_health_check():
    try:
        r = await get_redis_client()
        await r.ping()
        return {"status": "ok", "msg": "Redis connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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


# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")

# 템플릿 디렉토리 설정
templates = Jinja2Templates(directory="templates")

# mainpage.html 렌더링 ("/main" 라우트 대응)
@app.get("/main", response_class=HTMLResponse)
async def render_mainpage(request: Request):
    return templates.TemplateResponse("mainpage.html", {"request": request})
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI
    })


@app.post("/predict")
async def predict(months: int = Form(...), window_size: int = Form(12)):
    try:
        result = run_forecasting(window_size=window_size, forecast_horizon=months)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/chat/stream/")
async def stream_chat(request: ChatRequest):
    user_input = request.prompt
    months = request.months

    question_hash = hashlib.md5(user_input.encode()).hexdigest()
    cache_key = f"forecast_{months}_months_{question_hash}"
    cached_response = get_cached_forecast(cache_key)

    if cached_response:
        async def stream_cached():
            for c in cached_response:
                yield c
        return StreamingResponse(stream_cached(), media_type="text/plain")

    # 1. 예측값 생성
    forecast = await call_prediction_api(months, 12)
    prompt = build_forecast_prompt(user_input, forecast)

    # 2. GPT-1 호출 (요약 프롬프트)
    gpt_response = await get_openai_response(prompt)

    # 3. GPT-2 호출 (스트리밍)
    async def generate_final_response():
        full_response = ""
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": gpt_response}],
            stream=True
        )

        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                full_response += content
                yield content

        # ✅ 캐시와 Mongo 저장 (await 가능!)
        cache_forecast(cache_key, full_response)
        await save_generated_text(user_input, full_response)

    return StreamingResponse(generate_final_response(), media_type="text/plain")