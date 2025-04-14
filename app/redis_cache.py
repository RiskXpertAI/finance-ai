import logging
import httpx
import redis
import json
from fastapi import HTTPException
from app.config import REDIS_URL, PREDICT_API_URL
from app.utils.slack_alert import send_slack_alert

# Redis 클라이언트 생성
redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)

# ✅ Redis Client 반환
def get_redis_client():
    return redis_client


# ✅ 예측 데이터를 Redis에 저장
def cache_forecast(key: str, forecast_data: dict, expiration_time=3600):
    try:
        redis_client.setex(key, expiration_time, json.dumps(forecast_data))
        logging.info(f"[Redis] 캐시 저장 성공: {key}")
    except redis.ConnectionError as e:
        logging.error(f"[Redis] 연결 실패: {e}")
        send_slack_alert(f"[Redis] 연결 실패: {e}", level="ERROR")
    except Exception as e:
        logging.error(f"[Redis] 데이터 저장 오류: {e}")
        send_slack_alert(f"[Redis] 데이터 저장 오류: {e}", level="ERROR")


# ✅ Redis에서 예측 데이터 조회
def get_cached_forecast(cache_key: str):
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            logging.info(f"[Redis] 캐시 로드 성공: {cache_key}")
            return json.loads(cached_data)
        logging.info(f"[Redis] 캐시 없음: {cache_key}")
        return None
    except redis.ConnectionError as e:
        logging.error(f"[Redis] 연결 실패: {e}")
        send_slack_alert(f"[Redis] 연결 실패: {e}", level="ERROR")
        return None
    except Exception as e:
        logging.error(f"[Redis] 데이터 조회 오류: {e}")
        send_slack_alert(f"[Redis] 데이터 조회 오류: {e}", level="ERROR")
        return None


# ✅ 예측 API 호출
async def call_prediction_api(months: int, window_size: int):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            predict_response = await client.post(
                PREDICT_API_URL,
                data={"months": months, "window_size": window_size}
            )
            predict_response.raise_for_status()
            return predict_response.json()
    except httpx.ReadTimeout:
        logging.error("[PredictAPI] 호출 타임아웃")
        send_slack_alert("[PredictAPI] 호출 타임아웃", level="ERROR")
        raise HTTPException(status_code=504, detail="서버 응답 지연")
    except httpx.RequestError as e:
        logging.error(f"[PredictAPI] 요청 오류: {e}")
        send_slack_alert(f"[PredictAPI] 요청 오류: {e}", level="ERROR")
        raise HTTPException(status_code=500, detail="예측 API 요청 오류")
    except Exception as e:
        logging.error(f"[PredictAPI] 예측 API 오류: {e}")
        send_slack_alert(f"[PredictAPI] 예측 API 오류: {e}", level="ERROR")
        raise HTTPException(status_code=500, detail="예측 오류")