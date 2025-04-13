# 운영용 Dockerfile (ngrok 없음)
FROM python:3.10-slim

ARG ENV=production

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 코드 복사
COPY . .

# 포트 열기
EXPOSE 8000

# FastAPI 실행 (production 모드)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]