from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "software-distribution-api"}


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    db.execute(text("select 1"))
    return {"status": "ready", "database": "ok"}
