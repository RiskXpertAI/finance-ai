import hashlib
from http.client import HTTPException
from app.logger import *  # 로깅 설정만 로드

from fastapi.responses import StreamingResponse

from openai import OpenAI
from starlette.staticfiles import StaticFiles

from app.indicator import fetch_and_store_financial_data
from app.models import TextRequest

from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse


from fastapi import FastAPI, Form, Request
from app.services import get_openai_response, save_generated_text, build_forecast_prompt, get_scenario_based_answer
from app.redis_cache import cache_forecast, get_cached_forecast, call_prediction_api, get_redis_client
from app.transformer import run_forecasting, ChatRequest
from starlette.responses import JSONResponse
from app.routes import protected
from app.routes.auth import router as auth_router, KAKAO_CLIENT_ID, KAKAO_REDIRECT_URI  # 카카오 로그인 라우터

app = FastAPI()
client=OpenAI()

# 카카오 로그인
app.include_router(auth_router)

# ✅ 보호된 라우터 등록
app.include_router(protected.router)

templates = Jinja2Templates(directory="templates")

from app.health import api_router as health_router

app.include_router(health_router)

@app.get("/status")
async def read_root():
    return {"message": "MongoDB 연결 성공!"}


# Text 생성 API
@app.post("/generate_text/")
async def generate_text_and_save(request: TextRequest):
    logging.info(f"[Generate Text] 요청 시작 | Prompt: {request.prompt}")

    try:
        generated_text = await get_openai_response(request.prompt)
        logging.info(f"[Generate Text] 응답 완료 | {generated_text}")

        await save_generated_text(request.prompt, generated_text)
        logging.info("[Generate Text] MongoDB 저장 완료")

        return {"generated_text": generated_text}

    except Exception as e:
        logging.error(f"[Generate Text] 처리 실패 | Error: {e}")
        raise HTTPException(status_code=500, detail="텍스트 생성 실패")

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

    logging.info(f"[Chat Stream] 요청 시작 | Prompt: {user_input} | Months: {months}")

    question_hash = hashlib.md5(user_input.encode()).hexdigest()
    cache_key = f"forecast_{months}_months_{question_hash}"

    cached_response = get_cached_forecast(cache_key)
    if cached_response:
        logging.info(f"[Chat Stream] 캐시 데이터 활용 | CacheKey: {cache_key}")

        async def stream_cached():
            for c in cached_response:
                yield c
        return StreamingResponse(stream_cached(), media_type="text/plain")

    try:
        forecast = await call_prediction_api(months, 12)
        logging.info(f"[Chat Stream] 예측 데이터 생성 성공")

        prompt = build_forecast_prompt(user_input, forecast)
        gpt_response = await get_openai_response(prompt)
        logging.info(f"[Chat Stream] GPT 요약 응답 완료")

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

            cache_forecast(cache_key, full_response)
            await save_generated_text(user_input, full_response)
            logging.info(f"[Chat Stream] 최종 응답 캐시 및 저장 완료")

        return StreamingResponse(generate_final_response(), media_type="text/plain")

    except Exception as e:
        logging.error(f"[Chat Stream] 처리 실패 | Error: {e}")
        raise HTTPException(status_code=500, detail="챗봇 처리 실패")