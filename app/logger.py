import os
import logging

# 운영/개발 구분
ENV = os.getenv("ENV", "development")

if ENV == "production":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
else:
    logging.basicConfig(level=logging.DEBUG)