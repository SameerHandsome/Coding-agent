# app/db/redis.py
from upstash_redis import Redis
from app.core.config import settings
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

redis_client = Redis(url=settings.upstash_redis_url, token=settings.upstash_redis_token)

RATE_LIMITS = {"free": 10, "pro": 20}  # requests per 60-second window


def _key(user_id: str) -> str:
    minute = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    return f"rate_limit:{user_id}:{minute}"


def check_rate_limit(user_id: str, tier: str) -> bool:
    limit = RATE_LIMITS.get(tier, 3)
    try:
        count = redis_client.incr(_key(user_id))
        if count == 1:
            redis_client.expire(_key(user_id), 60)
        return count <= limit
    except Exception as e:
        logger.error(f"Redis error: {e} --- failing open")
        return True


def get_remaining_requests(user_id: str, tier: str) -> int:
    limit = RATE_LIMITS.get(tier, 3)
    try:
        current = redis_client.get(_key(user_id))
        return max(0, limit - (int(current) if current else 0))
    except Exception:
        return limit
