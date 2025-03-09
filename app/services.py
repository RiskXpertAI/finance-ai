import asyncio
import logging

from transformers import pipeline
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.llms import OpenAI
import openai

from app.database import collection  # MongoDB 연결
from app.config import OPENAI_API_KEY

# OpenAI API 키 설정
openai.api_key = OPENAI_API_KEY

# Hugging Face 모델 로드 (동기 실행)
generator = pipeline('text-generation', model='gpt2')

# 비동기로 Hugging Face 모델 실행
async def generate_text(prompt: str):
    loop = asyncio.get_running_loop()
    generated_text = await loop.run_in_executor(None, lambda: generator(prompt, max_length=200, truncation=True))
    return generated_text[0]['generated_text']

# OpenAI API 비동기 호출
async def get_openai_response(prompt: str):
    logging.info(f"🔵 OpenAI API 요청 시작: {prompt}")  # 요청 로그 찍기

    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, lambda: openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=150,
    ))

    logging.info(f"🟢 OpenAI 원본 응답: {response}")  # 응답 원본을 로그에 출력

    generated_text = response.choices[0].text.strip()
    logging.info(f"🟢 OpenAI API 응답 받음: {generated_text}")  # 가공된 응답 로그 찍기

    return generated_text


# MongoDB에 텍스트 저장
async def save_generated_text(prompt: str, generated_text: str):
    document = {"prompt": prompt, "generated_text": generated_text}
    result = await collection.insert_one(document)
    return result.inserted_id

# MongoDB에서 가장 최신 데이터 가져오기
async def get_stored_text():
    document = await collection.find_one(sort=[('_id', -1)])
    return document

# LangChain을 사용한 추가 분석
async def process_with_langchain():
    document = await get_stored_text()
    if not document:
        return "No data found in MongoDB"

    generated_text = document["generated_text"]

    # LangChain 설정
    prompt_template = "Given the following prompt, summarize or generate more information: {generated_text}"
    prompt_obj = PromptTemplate(input_variables=["generated_text"], template=prompt_template)

    llm = OpenAI(model_name="text-davinci-003", openai_api_key=OPENAI_API_KEY)
    llm_chain = LLMChain(prompt=prompt_obj, llm=llm)

    result = await llm_chain.arun(generated_text)
    return result
