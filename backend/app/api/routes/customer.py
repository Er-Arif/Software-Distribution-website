from datetime import UTC

from fastapi import APIRouter, Depends
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.db.models import BuildAsset, Device, Download, FileMetadata, InvoiceRecord, License, LicenseActivation, Notification, Order, Product, ProductVersion, SupportTicket, User
from app.services.licensing import is_license_usable

router = APIRouter()


def _as_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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


@router.get("/available-downloads")
def available_downloads(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(License, Product, ProductVersion, BuildAsset, FileMetadata)
        .join(Product, Product.id == License.product_id)
        .join(ProductVersion, ProductVersion.product_id == Product.id)
        .join(BuildAsset, BuildAsset.product_version_id == ProductVersion.id)
        .join(FileMetadata, FileMetadata.id == BuildAsset.file_id)
        .where(
            License.user_id == user.id,
            License.deleted_at.is_(None),
            ProductVersion.status == "published",
            ProductVersion.deleted_at.is_(None),
            BuildAsset.deleted_at.is_(None),
            FileMetadata.scan_status.in_(["clean", "trusted"]),
        )
        .order_by(Product.name, ProductVersion.published_at.desc().nullslast(), ProductVersion.created_at.desc())
    ).all()
    downloads = []
    for license_obj, product, version, build, file_obj in rows:
        if not is_license_usable(license_obj):
            continue
        published_at = _as_utc(version.published_at)
        update_access_expires_at = _as_utc(license_obj.update_access_expires_at)
        if published_at and update_access_expires_at and published_at > update_access_expires_at:
            continue
        downloads.append(
            {
                "product": product.name,
                "version": version.version,
                "build_id": str(build.id),
                "os": build.os,
                "architecture": build.architecture,
                "installer_type": build.installer_type,
                "checksum_sha256": build.checksum_sha256,
                "size_bytes": file_obj.size_bytes,
            }
        )
    return downloads


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
