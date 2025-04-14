from http.client import HTTPException

from fastapi import APIRouter

from app.database import database
from app.main import app
from app.redis_cache import get_redis_client
from app.utils.slack_alert import send_slack_alert

api_router = APIRouter(prefix="/api")


@app.get("/health/mongo")
async def mongo_health_check():
    try:
        await database.command("ping")
        send_slack_alert("[MongoDB OK] 연결 성공")  # ✅ 성공 알림
        return {"status": "ok", "msg": "MongoDB connected"}
    except Exception as e:
        send_slack_alert(f"[MongoDB Error] {e}")   # 실패 알림
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health/redis")
async def redis_health_check():
    try:
        r = await get_redis_client()
        await r.ping()
        return {"status": "ok", "msg": "Redis connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(api_router)