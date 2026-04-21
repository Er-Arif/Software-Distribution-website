from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.db.models import (
    AuditLog,
    DomainEvent,
    LegalDocument,
    License,
    LicensePolicy,
    Order,
    Payment,
    Plan,
    Product,
    ProductVersion,
    SupportTicket,
    User,
)
from app.schemas import AdminPlanCreate, AdminProductCreate
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


@router.get("/products")
def list_products(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Product).where(Product.deleted_at.is_(None)).order_by(Product.created_at.desc())).all()
    return [{"id": str(row.id), "name": row.name, "slug": row.slug, "status": row.status} for row in rows]


@router.post("/products")
def create_product(
    payload: AdminProductCreate,
    actor=Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    product = Product(**payload.model_dump())
    db.add(product)
    db.flush()
    audit(db, "product.create", "product", actor.id, str(product.id), {"slug": product.slug})
    db.commit()
    return {"id": str(product.id), "status": product.status}


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Plan).where(Plan.deleted_at.is_(None)).order_by(Plan.created_at.desc())).all()
    return [{"id": str(row.id), "code": row.code, "name": row.name, "price_amount": float(row.price_amount)} for row in rows]


@router.post("/plans")
def create_plan(
    payload: AdminPlanCreate,
    actor=Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    plan = Plan(**payload.model_dump())
    db.add(plan)
    db.flush()
    audit(db, "plan.create", "plan", actor.id, str(plan.id), {"code": plan.code})
    db.commit()
    return {"id": str(plan.id), "code": plan.code}


@router.get("/policies")
def policies(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(LicensePolicy).where(LicensePolicy.deleted_at.is_(None))).all()
    return [{"id": str(row.id), "name": row.name, "license_type": row.license_type, "max_devices": row.max_devices} for row in rows]


@router.get("/customers")
def customers(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(User).where(User.deleted_at.is_(None)).order_by(User.created_at.desc())).all()
    return [{"id": str(row.id), "email": row.email, "status": row.status, "roles": [role.name for role in row.roles]} for row in rows]


@router.post("/customers/{user_id}/suspend")
def suspend_customer(
    user_id: UUID,
    confirm: bool,
    actor=Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required for account suspension")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = "suspended"
    audit(db, "user.suspend", "user", actor.id, str(user.id), {"confirmed": True})
    db.commit()
    return {"status": "suspended"}


@router.get("/licenses")
def admin_licenses(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(License).where(License.deleted_at.is_(None)).order_by(License.created_at.desc())).all()
    return [{"id": str(row.id), "key": row.key, "status": row.status, "source": row.source} for row in rows]


@router.get("/orders")
def orders(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Order).where(Order.deleted_at.is_(None)).order_by(Order.created_at.desc())).all()
    return [{"id": str(row.id), "status": row.status, "total_amount": float(row.total_amount)} for row in rows]


@router.get("/payments")
def payments(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Payment).order_by(Payment.created_at.desc())).all()
    return [{"id": str(row.id), "provider": row.provider, "status": row.status, "amount": float(row.amount)} for row in rows]


@router.get("/versions")
def versions(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(ProductVersion).where(ProductVersion.deleted_at.is_(None)).order_by(ProductVersion.created_at.desc())).all()
    return [{"id": str(row.id), "version": row.version, "status": row.status, "forced_update": row.forced_update} for row in rows]


@router.post("/versions/{version_id}/publish")
def publish_version(
    version_id: UUID,
    confirm: bool,
    actor=Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required for release publish")
    version = db.get(ProductVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    version.status = "published"
    audit(db, "release.publish", "product_version", actor.id, str(version.id), {"confirmed": True})
    db.commit()
    return {"status": "published"}


@router.get("/support-tickets")
def support_tickets(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(SupportTicket).where(SupportTicket.deleted_at.is_(None)).order_by(SupportTicket.created_at.desc())).all()
    return [{"id": str(row.id), "subject": row.subject, "status": row.status, "priority": row.priority} for row in rows]


@router.get("/legal")
def legal_documents(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(LegalDocument).where(LegalDocument.deleted_at.is_(None)).order_by(LegalDocument.created_at.desc())).all()
    return [{"id": str(row.id), "type": row.document_type, "title": row.title, "version": row.version} for row in rows]


@router.get("/audit-logs")
def audit_logs(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)).all()
    return [{"action": row.action, "target_type": row.target_type, "target_id": row.target_id, "created_at": row.created_at} for row in rows]


@router.get("/events")
def events(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(DomainEvent).order_by(DomainEvent.created_at.desc()).limit(100)).all()
    return [{"event_type": row.event_type, "aggregate_type": row.aggregate_type, "payload": row.payload} for row in rows]


@router.post("/licenses/{license_id}/revoke")
def revoke_license(license_id: UUID, confirm: bool, actor=Depends(require_roles("super_admin", "admin")), db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required for license revocation")
    license_obj = db.get(License, license_id)
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    license_obj.status = "revoked"
    audit(db, "license.revoke", "license", actor.id, str(license_obj.id), {"confirmed": True})
    db.commit()
    return {"status": "revoked"}
