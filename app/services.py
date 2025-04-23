import asyncio
import logging
import openai

from app.database import generated_texts_collection
from app.config import OPENAI_API_KEY
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


# ✅ Forecast 프롬프트 생성
def build_forecast_prompt(user_input: str, forecast: dict, months: int):
    forecast_text = f"""
{months}개월 후 주요 지표는 다음과 같습니다:
- GDP: {forecast['GDP']:.3f}
- 환율: {forecast['환율']:.2f}
- 생산자물가지수: {forecast['생산자물가지수']:.2f}
- 소비자물가지수: {forecast['소비자물가지수']:.2f}
- 금리: {forecast['금리']:.2f}
"""

    prompt = f"""
```{forecast_text}```

[Note]
1. Summary는 400글자 내외로 작성.
2. Summary는 {{\\n}}을 포함할 수 없다.

출력은 반드시 한글로 작성하며 다음 양식을 따른다:

Summary: {{```로 둘러싸인 글의 요약}}

사용자 질문: {user_input}
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