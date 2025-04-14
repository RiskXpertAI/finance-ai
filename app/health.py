from fastapi import APIRouter, HTTPException
from app.database import database
from app.redis_cache import get_redis_client
from app.utils.slack_alert import send_slack_alert

api_router = APIRouter(prefix="/api")

@api_router.get("/health/mongo")
async def mongo_health_check():
    try:
        await database.command("ping")
        send_slack_alert("[MongoDB OK] 연결 성공")
        return {"status": "ok", "msg": "MongoDB connected"}
    except Exception as e:
        send_slack_alert(f"[MongoDB Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/health/redis")
async def redis_health_check():
    try:
        r = get_redis_client()
        r.ping()  # ✅ await 제거
        send_slack_alert("[Redis OK] 연결 성공")
        return {"status": "ok", "msg": "Redis connected"}
    except Exception as e:
        send_slack_alert(f"[Redis Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))