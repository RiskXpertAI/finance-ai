import hashlib
import logging

import httpx
from pydantic import ValidationError
from starlette.staticfiles import StaticFiles

from app.indicator import fetch_and_store_financial_data
from app.models import TextRequest
from app.database import database

from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse


from fastapi import FastAPI, HTTPException, Form, Request
from app.services import get_openai_response, save_generated_text, build_forecast_prompt, get_scenario_based_answer
from app.redis_cache import cache_forecast, get_cached_forecast, call_prediction_api
from app.transformer import run_forecasting, ChatRequest
from starlette.responses import JSONResponse
from app.routes import protected
from app.routes.auth import router as auth_router, KAKAO_CLIENT_ID, KAKAO_REDIRECT_URI  # 카카오 로그인 라우터

logging.basicConfig(level=logging.DEBUG)

app = FastAPI()


# 카카오 로그인
app.include_router(auth_router)

# ✅ 보호된 라우터 등록
app.include_router(protected.router)

templates = Jinja2Templates(directory="templates")


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



# @app.post("/chat/")
# async def chat(request: ChatRequest):
#     user_input = request.prompt  # 사용자가 입력한 질문
#     months = request.months  # 선택한 개월 수
#
#     # 1. transformer 예측값 가져오기 (httpx 사용)
#     async with httpx.AsyncClient() as client:  # httpx.AsyncClient 사용
#         predict_response = await client.post(
#             # "http://localhost:8000/predict",  # 예측 엔드포인트로 수정 필요
#             "http://host.docker.internal:8000/predict",  # 도커 내에서 외부 API 호출 시 수정 필요
#
#             data={"months": months, "window_size": 12}
#         )
#
#     if predict_response.status_code != 200:
#         raise HTTPException(status_code=500, detail="예측 오류")
#
#     forecast = predict_response.json()  # 예측 결과 가져오기
#     forecast_text = "\n".join([f"{k}: {v:.2f}" for k, v in forecast.items() if k != "TIME"])
#
#     # 2. 프롬프트 생성
#     prompt = build_forecast_prompt(user_input, forecast)
#
#     # 3. GPT에 요청
#     response_text = await get_openai_response(prompt)
#     await save_generated_text(user_input, response_text)
#
#     return {"response": response_text}  # JSON 형식으로 응답


# Redis 캐시에서 예측값을 확인하는 함수
@app.post("/chat/")
async def chat(request: ChatRequest):
    try:
        user_input = request.prompt  # 사용자가 입력한 질문
        months = request.months  # 선택한 개월 수
        logging.debug(f'user_input: {user_input}, months: {months}')
    except ValidationError as e:
        logging.debug(f"Validation error: {e.errors()}")  # 유효성 검사 오류 출력
        raise HTTPException(status_code=422, detail=f"Validation error: {e.errors()}")

    # 서버에서 데이터 확인을 위한 추가 로그
    logging.debug(f"User input: {user_input}, months: {months}")

    # 질문을 해시화하여 캐시 키를 다르게 생성
    question_hash = hashlib.md5(user_input.encode()).hexdigest()  # 질문을 해시화
    cache_key = f"forecast_{months}_months_{question_hash}"  # 캐시 키에 질문 해시 추가
    logging.debug(f"🔍 Redis 캐시에서 예측값을 확인 중... 캐시 키: {cache_key}")

    forecast = get_cached_forecast(cache_key)
    if forecast:
        # Redis에 예측값이 이미 있으면 그대로 반환
        logging.debug(f"🔵 Redis에서 캐시된 예측값 로드 성공: {forecast}")
        return forecast  # 예측값을 그대로 반환 (GPT 로직은 돌리지 않음)

    else:
        # Redis에 예측값이 없으면 예측 API를 호출하고, GPT 로직을 돌린다.
        logging.debug(f"🔴 Redis에 캐시된 예측값이 없어서 새로운 예측을 진행합니다.")
        forecast = await call_prediction_api(months, 12)  # 예측 API 호출
        logging.debug(f"🟢 예측 결과가 성공적으로 반환되었습니다: {forecast}")

        # 예측값을 사용하여 GPT 응답 생성
        prompt_for_gpt = build_forecast_prompt(user_input, forecast)
        logging.debug(f"🔵 생성된 GPT 프롬프트: {prompt_for_gpt}")

        # GPT-1 응답 생성
        gpt_response = await get_openai_response(prompt_for_gpt)
        logging.debug(f"🟢 GPT-1 응답: {gpt_response}")

        # GPT-2로 추가 답변 생성
        final_response = await get_scenario_based_answer(gpt_response)
        logging.debug(f"🟢 GPT-2 응답: {final_response}")

        # 최종 GPT 응답을 Redis에 저장
        cache_forecast(cache_key, final_response)  # 최종 GPT 응답을 Redis에 캐시
        await save_generated_text(user_input, final_response)  # MongoDB에 저장

        return final_response