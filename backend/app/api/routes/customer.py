from fastapi import APIRouter, Depends
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.db.models import Device, Download, InvoiceRecord, License, LicenseActivation, Notification, Order, Product, SupportTicket, User

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


@router.get("/products")
def purchased_products(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(Product, License)
        .join(License, License.product_id == Product.id)
        .where(License.user_id == user.id, License.deleted_at.is_(None))
    ).all()
    return [{"product": {"id": str(product.id), "name": product.name, "slug": product.slug}, "license_status": license.status} for product, license in rows]


@router.get("/devices")
def devices(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Device).where(Device.user_id == user.id, Device.deleted_at.is_(None))).all()
    return [{"id": str(row.id), "label": row.machine_label, "status": row.status, "fingerprint_version": row.fingerprint_version} for row in rows]


@router.post("/devices/{device_id}/deactivate")
def deactivate_device(device_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    device = db.get(Device, device_id)
    if not device or device.user_id != user.id:
        return {"status": "not_found"}
    device.status = "deactivated"
    activations = db.scalars(select(LicenseActivation).where(LicenseActivation.device_id == device.id)).all()
    for activation in activations:
        activation.status = "deactivated"
    db.commit()
    return {"status": "deactivated"}


@router.get("/downloads")
def downloads(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Download).where(Download.user_id == user.id).order_by(Download.created_at.desc())).all()
    return [{"id": str(row.id), "status": row.status, "product_id": str(row.product_id), "created_at": row.created_at} for row in rows]


@router.get("/billing")
def billing(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    orders = db.scalars(select(Order).where(Order.user_id == user.id, Order.deleted_at.is_(None))).all()
    invoices = db.scalars(
        select(InvoiceRecord).join(Order, Order.id == InvoiceRecord.order_id).where(Order.user_id == user.id)
    ).all()
    return {
        "orders": [{"id": str(row.id), "status": row.status, "total_amount": float(row.total_amount)} for row in orders],
        "invoices": [{"id": str(row.id), "invoice_number": row.invoice_number, "status": row.status} for row in invoices],
    }


@router.get("/support-tickets")
def tickets(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(SupportTicket).where(SupportTicket.user_id == user.id, SupportTicket.deleted_at.is_(None))).all()
    return [{"id": str(row.id), "subject": row.subject, "status": row.status, "priority": row.priority} for row in rows]


@router.get("/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc())).all()
    return [{"id": str(row.id), "title": row.title, "body": row.body, "read_at": row.read_at} for row in rows]
