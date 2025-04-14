import os
import logging

ENV = os.getenv("ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

log_format = "%(asctime)s - %(levelname)s - %(message)s"

# 기본 로깅 설정
logging.basicConfig(level=LOG_LEVEL, format=log_format)

# noisy 라이브러리 로그레벨 낮추기
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.INFO)
logging.getLogger("uvicorn").setLevel(logging.INFO)