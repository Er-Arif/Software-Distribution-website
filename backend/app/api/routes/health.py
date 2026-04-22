from fastapi import APIRouter, Depends
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.storage import storage_service

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "software-distribution-api"}


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    db.execute(text("select 1"))
    redis_status = "ok"
    try:
        Redis.from_url(settings.redis_url, socket_connect_timeout=1).ping()
    except Exception:
        redis_status = "unavailable"
    storage_status = "ok" if storage_service.client is not None or settings.storage_backend == "local" else "degraded"
    return {"status": "ready", "database": "ok", "redis": redis_status, "storage": storage_status}


@router.get("/metrics")
def metrics() -> dict:
    return {
        "service": "software-distribution-api",
        "metrics": {
            "health_checks": 1,
            "error_tracking_configured": bool(settings.sentry_dsn),
        },
    }
