import asyncio
import logging
import openai

from app.database import generated_texts_collection  # MongoDB 연결
from app.config import OPENAI_API_KEY  # 환경 변수에서 OpenAI API 키 가져오기

# ✅ OpenAI API 설정
client = openai.OpenAI(api_key=OPENAI_API_KEY)  # OpenAI API 클라이언트 인스턴스 생성

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# INFO 레벨 이상의 로그를 출력하고, 시간/레벨/메시지를 포함하는 로그 포맷 설정

# ✅ OpenAI API 요청 함수
async def get_openai_response(prompt: str):
    """
    OpenAI API를 호출하여 사용자 프롬프트(prompt)에 대한 응답을 생성하는 함수.

    Args:
        prompt (str): 사용자가 입력한 프롬프트 (질문 또는 요청).

    Returns:
        str: OpenAI에서 생성한 응답 텍스트.
    """
    logging.info(f"🔵 OpenAI API 요청 시작: {prompt}")  # API 요청 로그 기록

    loop = asyncio.get_running_loop()  # 현재 실행 중인 이벤트 루프 가져오기
    response = await loop.run_in_executor(None, lambda: client.chat.completions.create(
        model="gpt-3.5-turbo",  # 사용할 GPT 모델 (gpt-3.5-turbo)
        messages=[{"role": "user", "content": prompt}],  # 사용자 메시지를 포함한 대화 기록
        max_tokens=150,  # 최대 토큰 수 (150 토큰까지 생성)
    ))

    logging.info(f"🟢 OpenAI API 원본 응답: {response}")  # API 원본 응답 로그 기록
    generated_text = response.choices[0].message.content.strip()  # 응답에서 텍스트만 추출 및 공백 제거
    logging.info(f"🟢 OpenAI API 최종 응답: {generated_text}")  # 최종 응답 로그 기록

    return generated_text  # OpenAI가 생성한 응답 반환


# ✅ MongoDB에 텍스트 저장
async def save_generated_text(prompt: str, generated_text: str):
    """
    사용자의 프롬프트와 OpenAI에서 생성된 텍스트를 MongoDB에 저장하는 함수.

    Args:
        prompt (str): 사용자가 입력한 프롬프트.
        generated_text (str): OpenAI가 생성한 응답 텍스트.

    Returns:
        ObjectId: 저장된 문서의 MongoDB ObjectId.
    """
    logging.info(f"💾 MongoDB에 데이터 저장: {prompt} -> {generated_text}")  # 저장 작업 로그 기록
    document = {"prompt": prompt, "generated_text": generated_text}  # 저장할 문서 생성
    result = await generated_texts_collection.insert_one(document)  # MongoDB에 문서 저장 (비동기 실행)
    return result.inserted_id  # 저장된 문서의 ObjectId 반환


# ✅ MongoDB에서 가장 최신 데이터 가져오기
async def get_stored_text():
    """
    MongoDB에서 가장 최근에 저장된 프롬프트 및 생성된 텍스트를 가져오는 함수.

    Returns:
        dict or None: 가장 최신의 문서 반환 (없으면 None 반환).
    """
    logging.info("📥 MongoDB에서 최신 데이터 가져오기")  # 데이터 조회 로그 기록
    document = await generated_texts_collection.find_one(sort=[('_id', -1)])  # 최신 데이터 1개 가져오기
    if not document:
        logging.warning("⚠️ MongoDB에 데이터가 없음!")  # 데이터가 없으면 경고 로그 출력
    return document  # 가져온 문서 반환 (없으면 None)
