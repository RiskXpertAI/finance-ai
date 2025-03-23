import redis
import json
from app.config import REDIS_URL

# Redis 클라이언트 생성
redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)

# 예측 데이터를 Redis에 저장하는 함수
def cache_forecast(key: str, forecast_data: dict, expiration_time=3600):
    """ 예측 데이터를 Redis에 저장 """
    redis_client.setex(key, expiration_time, json.dumps(forecast_data))

# Redis에서 예측 데이터를 가져오는 함수
def get_cached_forecast(cache_key: str):
    """
    Redis에서 예측값을 가져오는 함수.
    캐시된 예측값이 없으면 None을 반환.
    """
    cached_data = redis_client.get(cache_key)  # 캐시된 데이터 가져오기
    if cached_data:
        return json.loads(cached_data)  # JSON 형식으로 변환하여 반환
    return None