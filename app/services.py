import asyncio
import logging
import openai
from pymongo import MongoClient

from app.database import generated_texts_collection
from app.config import OPENAI_API_KEY, MONGO_URI
from app.utils.slack_alert import send_slack_alert

# OpenAI Client 생성
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ✅ OpenAI API 응답 요청
async def get_openai_response(prompt: str):
    logging.info(f"[OpenAI] 요청 시작 | Prompt: {prompt}")

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        ))
    except Exception as e:
        logging.error(f"[OpenAI] API 호출 실패 | Error: {e}")
        send_slack_alert(f"[OpenAI] API 호출 실패 | Error: {e}", level="ERROR")
        raise

    logging.info(f"[OpenAI] 원본 응답 수신 완료")
    generated_text = response.choices[0].message.content.strip()
    logging.info(f"[OpenAI] 최종 응답 | {generated_text}")

    return generated_text


# ✅ MongoDB 저장
async def save_generated_text(prompt: str, generated_text: str):
    logging.info(f"[MongoDB] 데이터 저장 시도 | Prompt: {prompt} -> Response: {generated_text}")

    document = {
        "prompt": prompt,
        "generated_text": generated_text
    }

    try:
        result = await generated_texts_collection.insert_one(document)
    except Exception as e:
        logging.error(f"[MongoDB] 저장 실패 | Error: {e}")
        send_slack_alert(f"[MongoDB] 저장 실패 | Error: {e}", level="ERROR")
        raise

    logging.info(f"[MongoDB] 저장 완료 | Document ID: {result.inserted_id}")
    return result.inserted_id

# ✅ MongoDB 최신 데이터 조회
async def get_stored_text():
    logging.info("[MongoDB] 최신 데이터 조회 시도")

    document = await generated_texts_collection.find_one(sort=[('_id', -1)])
    if not document:
        logging.warning("[MongoDB] 데이터 없음")

    return document

def get_latest_data_from_db():
    client = MongoClient(MONGO_URI)
    db = client["financeai"]
    collection = db["financial_data"]
    latest = collection.find_one(sort=[("TIME", -1)], projection={"_id": 0})
    print("[현재 데이터]", latest)  # ✅ 디버깅용 출력 추가
    return latest


# ✅ Forecast 프롬프트 생성
def build_forecast_prompt(user_input: str, forecast: dict, months: int, current_data: dict):
    def f(val):
        try:
            return float(val)
        except:
            return 0.0

    prompt = f"""
당신은 한국의 거시경제 예측 전문가입니다. 아래 현재 및 예측 데이터를 기반으로 사용자의 질문에 답하세요.

[작성 지침]
- 반드시 **정확한 수치 기반 비교**를 포함할 것
- **논리적이고 자연스러운 문장**으로 구성
- **경제 기사 스타일의 어휘** 사용 (예: 경기 둔화, 물가 상승 압력 등)
- 어색하거나 불완전한 표현 금지 (예: "절 변화" 같은 잘못된 문장 제거)
- 아래 형식을 엄격히 따를 것

# 현재 시점 주요 경제 지표
- GDP: {f(current_data['GDP']):.3f}
- 환율: {f(current_data['환율']):.2f}
- 생산자물가지수(PPI): {f(current_data['생산자물가지수']):.2f}
- 소비자물가지수(CPI): {f(current_data['소비자물가지수']):.2f}
- 금리: {f(current_data['금리']):.2f}

# {months}개월 후 예측된 경제 지표
- GDP: {forecast['GDP']:.3f}
- 환율: {forecast['환율']:.2f}
- 생산자물가지수(PPI): {forecast['생산자물가지수']:.2f}
- 소비자물가지수(CPI): {forecast['소비자물가지수']:.2f}
- 금리: {forecast['금리']:.2f}

# 사용자 질문
{user_input}

# 응답 형식 (형식 반드시 지켜야 함)
Summary: {{```400자 내외의 한글 요약. 반드시 예측 금리 수치 포함```}}

Reasoning: {{```현재와 예측 수치를 비교하고, 금리 변화의 원인을 수치 기반으로 설명```}}
"""
    return prompt

# ✅ GPT-2 응답 처리
async def get_scenario_based_answer(prompt: str):
    logging.info(f"[OpenAI] GPT-2 요청 시작 | Prompt: {prompt}")

    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, lambda: client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
    ))

    logging.info(f"[OpenAI] GPT-2 원본 응답 수신 완료")
    generated_text = response.choices[0].message.content.strip()
    logging.info(f"[OpenAI] GPT-2 최종 응답 | {generated_text}")

    return generated_text