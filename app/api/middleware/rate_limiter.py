# app/api/middleware/rate_limiter.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.security import verify_token
from app.db.redis import RATE_LIMITS
from app.db.redis import check_rate_limit, get_remaining_requests

SKIP_PATHS = {
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/health",
}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return await call_next(request)

        try:
            payload = verify_token(auth.split(" ", 1)[1])
            user_id, tier = payload["user_id"], payload["tier"]
        except Exception:
            return await call_next(request)

        if not check_rate_limit(user_id, tier):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Limit: {RATE_LIMITS.get(tier, 10)}/min",
                    "retry_after": 60,
                    "remaining": get_remaining_requests(user_id, tier),
                },
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
