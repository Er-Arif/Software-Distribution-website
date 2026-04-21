from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.db.models import AuditLog, DomainEvent, License, Order, Payment, Product, User
from app.services.events import audit

router = APIRouter(dependencies=[Depends(require_roles("super_admin", "admin", "support"))])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)) -> dict:
    return {
        "products": db.scalar(select(func.count(Product.id)).where(Product.deleted_at.is_(None))),
        "customers": db.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None))),
        "orders": db.scalar(select(func.count(Order.id)).where(Order.deleted_at.is_(None))),
        "active_licenses": db.scalar(select(func.count(License.id)).where(License.status == "active")),
        "failed_payments": db.scalar(select(func.count(Payment.id)).where(Payment.status == "failed")),
    }


@router.get("/audit-logs")
def audit_logs(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)).all()
    return [{"action": row.action, "target_type": row.target_type, "target_id": row.target_id, "created_at": row.created_at} for row in rows]


@router.get("/events")
def events(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(DomainEvent).order_by(DomainEvent.created_at.desc()).limit(100)).all()
    return [{"event_type": row.event_type, "aggregate_type": row.aggregate_type, "payload": row.payload} for row in rows]


@router.post("/licenses/{license_id}/revoke")
def revoke_license(license_id: str, confirm: bool, actor=Depends(require_roles("super_admin", "admin")), db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required for license revocation")
    license_obj = db.get(License, license_id)
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    license_obj.status = "revoked"
    audit(db, "license.revoke", "license", actor.id, str(license_obj.id), {"confirmed": True})
    db.commit()
    return {"status": "revoked"}
