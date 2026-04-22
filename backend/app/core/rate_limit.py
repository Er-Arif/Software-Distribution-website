from dataclasses import dataclass
from time import time

from fastapi import HTTPException, Request, status
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings


@dataclass(frozen=True)
class RateLimitPolicy:
    name: str
    max_requests: int
    window_seconds: int


POLICIES = {
    "auth": RateLimitPolicy("auth", 10, 60),
    "license": RateLimitPolicy("license", 60, 60),
    "download": RateLimitPolicy("download", 20, 60),
    "public": RateLimitPolicy("public", 300, 60),
}

_memory_store: dict[str, list[float]] = {}
_redis_client: Redis | None = None


def _redis() -> Redis | None:
    global _redis_client
    if settings.app_env == "test":
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        _redis_client = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=1)
        _redis_client.ping()
        return _redis_client
    except RedisError:
        _redis_client = None
        return None


def rate_limit(category: str):
    async def dependency(request: Request) -> None:
        policy = POLICIES[category]
        forwarded = request.headers.get("x-forwarded-for", "")
        ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
        key = f"{policy.name}:{ip}"
        now = time()
        redis = _redis()
        if redis:
            bucket_key = f"rate:{key}:{int(now // policy.window_seconds)}"
            try:
                count = redis.incr(bucket_key)
                if count == 1:
                    redis.expire(bucket_key, policy.window_seconds)
                if count > policy.max_requests:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={"code": "rate_limited", "message": "Too many requests"},
                    )
                return
            except RedisError:
                pass
        window_start = now - policy.window_seconds
        hits = [hit for hit in _memory_store.get(key, []) if hit >= window_start]
        if len(hits) >= policy.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "rate_limited", "message": "Too many requests"},
            )
        hits.append(now)
        _memory_store[key] = hits

    return dependency
