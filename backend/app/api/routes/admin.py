from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.db.models import (
    AuditLog,
    BuildAsset,
    DomainEvent,
    FileMetadata,
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
from app.schemas import (
    AdminBuildCreate,
    AdminLegalDocumentUpsert,
    AdminLicenseCreate,
    AdminPlanCreate,
    AdminPolicyCreate,
    AdminProductCreate,
    AdminVersionCreate,
)
from app.services.events import audit, emit_event
from app.services.licensing import create_manual_license
from datetime import UTC, datetime

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


@router.get("/analytics")
def analytics(db: Session = Depends(get_db)) -> dict:
    revenue = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == "paid"))
    return {
        "revenue": float(revenue or 0),
        "products": db.scalar(select(func.count(Product.id)).where(Product.deleted_at.is_(None))),
        "customers": db.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None))),
        "active_licenses": db.scalar(select(func.count(License.id)).where(License.status == "active")),
        "failed_payments": db.scalar(select(func.count(Payment.id)).where(Payment.status == "failed")),
        "published_versions": db.scalar(select(func.count(ProductVersion.id)).where(ProductVersion.status == "published")),
        "open_tickets": db.scalar(select(func.count(SupportTicket.id)).where(SupportTicket.status == "open")),
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


@router.post("/policies")
def create_policy(
    payload: AdminPolicyCreate,
    actor=Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    policy = LicensePolicy(**payload.model_dump())
    db.add(policy)
    db.flush()
    audit(db, "policy.create", "license_policy", actor.id, str(policy.id), {"name": policy.name})
    db.commit()
    return {"id": str(policy.id), "name": policy.name}


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


@router.post("/licenses")
def create_license(
    payload: AdminLicenseCreate,
    actor=Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    license_obj = create_manual_license(
        db,
        payload.user_id,
        payload.product_id,
        payload.policy_id,
        payload.source,
        payload.expires_at,
    )
    license_obj.plan_id = payload.plan_id
    license_obj.max_devices_override = payload.max_devices_override
    audit(db, "license.create", "license", actor.id, str(license_obj.id), {"source": payload.source})
    db.commit()
    return {"id": str(license_obj.id), "key": license_obj.key, "status": license_obj.status}


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


@router.post("/versions")
def create_version(
    payload: AdminVersionCreate,
    actor=Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    version = ProductVersion(**payload.model_dump())
    db.add(version)
    db.flush()
    audit(db, "release.create", "product_version", actor.id, str(version.id), {"version": version.version})
    db.commit()
    return {"id": str(version.id), "status": version.status}


@router.post("/builds")
def create_build(
    payload: AdminBuildCreate,
    actor=Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    file_obj = FileMetadata(
        bucket=payload.bucket,
        object_key=payload.object_key,
        visibility="private",
        mime_type="application/octet-stream",
        size_bytes=payload.size_bytes,
        sha256=payload.checksum_sha256,
        scan_status="pending",
    )
    db.add(file_obj)
    db.flush()
    build = BuildAsset(
        product_version_id=payload.product_version_id,
        file_id=file_obj.id,
        os=payload.os,
        architecture=payload.architecture,
        installer_type=payload.installer_type,
        checksum_sha256=payload.checksum_sha256,
        code_signature_status=payload.code_signature_status,
        minimum_supported_version=payload.minimum_supported_version,
    )
    db.add(build)
    db.flush()
    audit(db, "build.create", "build_asset", actor.id, str(build.id), {"object_key": payload.object_key})
    db.commit()
    return {"id": str(build.id), "checksum_sha256": build.checksum_sha256}


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
    version.published_at = datetime.now(UTC)
    audit(db, "release.publish", "product_version", actor.id, str(version.id), {"confirmed": True})
    db.commit()
    return {"status": "published"}


@router.post("/versions/{version_id}/rollback")
def rollback_version(
    version_id: UUID,
    fallback_version_id: UUID,
    confirm: bool,
    actor=Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required for release rollback")
    version = db.get(ProductVersion, version_id)
    fallback = db.get(ProductVersion, fallback_version_id)
    if not version or not fallback:
        raise HTTPException(status_code=404, detail="Version not found")
    version.rollback_to_version_id = fallback.id
    audit(db, "release.rollback", "product_version", actor.id, str(version.id), {"fallback": str(fallback.id)})
    emit_event(db, "release.rollback", "product_version", str(version.id), {"fallback": str(fallback.id)})
    db.commit()
    return {"status": "rollback_configured"}


@router.get("/support-tickets")
def support_tickets(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(SupportTicket).where(SupportTicket.deleted_at.is_(None)).order_by(SupportTicket.created_at.desc())).all()
    return [{"id": str(row.id), "subject": row.subject, "status": row.status, "priority": row.priority} for row in rows]


@router.post("/support-tickets/{ticket_id}/close")
def close_ticket(
    ticket_id: UUID,
    actor=Depends(require_roles("super_admin", "admin", "support")),
    db: Session = Depends(get_db),
) -> dict:
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.status = "closed"
    audit(db, "support.close", "support_ticket", actor.id, str(ticket.id), {})
    db.commit()
    return {"status": "closed"}


@router.get("/legal")
def legal_documents(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(LegalDocument).where(LegalDocument.deleted_at.is_(None)).order_by(LegalDocument.created_at.desc())).all()
    return [{"id": str(row.id), "type": row.document_type, "title": row.title, "version": row.version} for row in rows]


@router.post("/legal")
def upsert_legal_document(
    payload: AdminLegalDocumentUpsert,
    actor=Depends(require_roles("super_admin", "admin")),
    db: Session = Depends(get_db),
) -> dict:
    document = LegalDocument(
        document_type=payload.document_type,
        title=payload.title,
        body=payload.body,
        version=payload.version,
        published_at=datetime.now(UTC) if payload.publish else None,
    )
    db.add(document)
    db.flush()
    audit(db, "legal.publish", "legal_document", actor.id, str(document.id), {"type": payload.document_type})
    db.commit()
    return {"id": str(document.id), "published": bool(document.published_at)}


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
