# 로컬/프로덕션 구분을 위한 환경 변수 설정

# 빌드 시점에서만 사용되는 환경 변수
ARG ENV=development

# 베이스 이미지
FROM python:3.10-slim

# ngrok 설치 (ngrok을 설치하려면 wget과 unzip이 필요)
RUN apt-get update && apt-get install -y wget unzip curl

# ngrok 설치 (APT를 사용하여)
RUN curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
  | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
  && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
  | tee /etc/apt/sources.list.d/ngrok.list \
  && apt-get update \
  && apt-get install ngrok


COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 포트 오픈
EXPOSE 8000

# 로컬 개발 환경과 프로덕션 환경에 따라 다르게 실행하도록 설정
# 로컬 환경에서는 --reload, 프로덕션 환경에서는 --workers

# 조건문을 통해 로컬/프로덕션 구분하여 실행
CMD ["sh", "-c", "if [ \"$ENV\" = \"development\" ]; then uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload; else uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4; fi"]

#1.	로컬 개발 환경에서 빌드 및 실행
#docker build --build-arg ENV=development -t financeai-image:v1.0 .
#docker run -e ENV=development -p 8000:8000 financeai-image:v1.0

#2.	프로덕션 환경에서 빌드 및 실행
#docker build --build-arg ENV=production -t financeai-image:v1.0 .
#docker run -e ENV=production -p 8000:8000 financeai-image:v1.0