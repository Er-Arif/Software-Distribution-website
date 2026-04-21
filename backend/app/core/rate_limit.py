from dataclasses import dataclass
from time import time

from fastapi import HTTPException, Request, status


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


def rate_limit(category: str):
    async def dependency(request: Request) -> None:
        policy = POLICIES[category]
        forwarded = request.headers.get("x-forwarded-for", "")
        ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
        key = f"{policy.name}:{ip}"
        now = time()
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
