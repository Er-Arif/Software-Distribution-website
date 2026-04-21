from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.db.models import Download, License, Notification, Order, User

router = APIRouter()


@router.get("/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    licenses = db.scalars(select(License).where(License.user_id == user.id, License.deleted_at.is_(None))).all()
    orders = db.scalars(select(Order).where(Order.user_id == user.id, Order.deleted_at.is_(None))).all()
    downloads = db.scalars(select(Download).where(Download.user_id == user.id).order_by(Download.created_at.desc())).all()
    return {
        "licenses": len(licenses),
        "orders": len(orders),
        "downloads": len(downloads),
        "active_licenses": len([item for item in licenses if item.status == "active"]),
    }


@router.get("/licenses")
def licenses(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(License).where(License.user_id == user.id, License.deleted_at.is_(None))).all()
    return [
        {
            "id": str(row.id),
            "key": row.key,
            "status": row.status,
            "expires_at": row.expires_at,
            "update_access_expires_at": row.update_access_expires_at,
        }
        for row in rows
    ]


@router.get("/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc())).all()
    return [{"id": str(row.id), "title": row.title, "body": row.body, "read_at": row.read_at} for row in rows]
