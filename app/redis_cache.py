import logging
import httpx
import redis
import json
from fastapi import HTTPException
from app.config import REDIS_URL

# Redis 클라이언트 생성
redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)

# 예측 데이터를 Redis에 저장하는 함수
def cache_forecast(key: str, forecast_data: dict, expiration_time=3600):
    """ 예측 데이터를 Redis에 저장 """
    try:
        redis_client.setex(key, expiration_time, json.dumps(forecast_data))
        logging.info(f"🔵 캐시된 예측 데이터 저장 성공: {key}")
    except redis.ConnectionError as e:
        logging.error(f"Redis 연결 실패: {e}")
    except Exception as e:
        logging.error(f"Redis 데이터 저장 오류: {e}")

# Redis에서 예측 데이터를 가져오는 함수
def get_cached_forecast(cache_key: str):
    """
    Redis에서 예측값을 가져오는 함수.
    캐시된 예측값이 없으면 None을 반환.
    """
    try:
        cached_data = redis_client.get(cache_key)  # 캐시된 데이터 가져오기
        if cached_data:
            logging.info(f"🔵 캐시된 예측 데이터 로드 성공: {cache_key}")
            return json.loads(cached_data)  # JSON 형식으로 변환하여 반환
        logging.info(f"🔴 캐시된 예측 데이터 없음: {cache_key}")
        return None
    except redis.ConnectionError as e:
        logging.error(f"Redis 연결 실패: {e}")
        return None
    except Exception as e:
        logging.error(f"Redis 데이터 조회 오류: {e}")
        return None

# 예측 API 호출
async def call_prediction_api(months: int, window_size: int):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:  # 타임아웃 10초로 설정
            predict_response = await client.post(
                "https://59b7-118-131-63-236.ngrok-free.app/predict",
                data={"months": months, "window_size": window_size}
            )
            predict_response.raise_for_status()  # 상태 코드가 200이 아니면 예외 발생
            return predict_response.json()  # 예측 결과 반환
    except httpx.ReadTimeout:
        logging.error("예측 API 호출 타임아웃")
        raise HTTPException(status_code=504, detail="서버 응답 지연")
    except httpx.RequestError as e:
        logging.error(f"예측 API 요청 오류: {e}")
        raise HTTPException(status_code=500, detail="예측 API 요청 오류")
    except Exception as e:
        logging.error(f"예측 API 오류: {e}")
        raise HTTPException(status_code=500, detail="예측 오류")
