from datetime import UTC, datetime, timedelta
from hashlib import sha256

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import generate_license_key
from app.core.signing import sign_payload
from app.db.models import (
    Device,
    Entitlement,
    License,
    LicenseActivation,
    LicensePolicy,
    Product,
)
from app.schemas import FingerprintInput
from app.services.abuse import detect_activation_abuse
from app.services.events import emit_event


def fingerprint_hash(fingerprint: FingerprintInput) -> str:
    basis = "|".join(
        [
            fingerprint.version,
            fingerprint.machine_id or "",
            fingerprint.os,
            fingerprint.os_version or "",
            fingerprint.app_installation_id,
            fingerprint.cpu_hash or "",
            fingerprint.motherboard_hash or "",
            fingerprint.fallback_hash or "",
        ]
    )
    return sha256(basis.encode("utf-8")).hexdigest()


def create_manual_license(
    db: Session,
    user_id,
    product_id,
    policy_id,
    source: str = "manual",
    expires_at: datetime | None = None,
) -> License:
    license_obj = License(
        user_id=user_id,
        product_id=product_id,
        policy_id=policy_id,
        key=generate_license_key(),
        source=source,
        starts_at=datetime.now(UTC),
        expires_at=expires_at,
    )
    db.add(license_obj)
    db.flush()
    emit_event(db, "license.issued", "license", str(license_obj.id), {"source": source})
    return license_obj


def _load_license(db: Session, license_key: str, product_slug: str) -> tuple[License, Product]:
    row = db.execute(
        select(License, Product)
        .join(Product, Product.id == License.product_id)
        .where(License.key == license_key, Product.slug == product_slug, License.deleted_at.is_(None))
    ).first()
    if not row:
        emit_event(db, "license.validation_failed", "license", None, {"reason": "not_found"})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="License not found")
    return row[0], row[1]


def _license_state(license_obj: License) -> str:
    now = datetime.now(UTC)
    if license_obj.status in {"revoked", "suspended", "blacklisted"}:
        return license_obj.status
    if license_obj.expires_at and license_obj.expires_at < now:
        return "expired"
    return license_obj.status


def _entitlements(db: Session, license_obj: License) -> dict:
    rows = db.scalars(
        select(Entitlement).where(
            Entitlement.enabled.is_(True),
            Entitlement.deleted_at.is_(None),
            (Entitlement.license_id == license_obj.id)
            | (Entitlement.plan_id == license_obj.plan_id)
            | (Entitlement.user_id == license_obj.user_id)
            | (Entitlement.product_id == license_obj.product_id),
        )
    ).all()
    return {row.feature_key: row.value for row in rows}


def activate_license(
    db: Session,
    license_key: str,
    product_slug: str,
    app_version: str,
    fingerprint: FingerprintInput,
    device_label: str | None,
    ip_address: str | None,
) -> dict:
    license_obj, product = _load_license(db, license_key, product_slug)
    state = _license_state(license_obj)
    if state in {"revoked", "suspended", "blacklisted"}:
        raise HTTPException(status_code=403, detail=f"License is {state}")

    fp_hash = fingerprint_hash(fingerprint)
    policy: LicensePolicy = license_obj.policy
    max_devices = license_obj.max_devices_override or policy.max_devices

    device = db.scalar(select(Device).where(Device.fingerprint_hash == fp_hash, Device.user_id == license_obj.user_id))
    if not device:
        active_count = db.scalar(
            select(func.count(LicenseActivation.id))
            .where(LicenseActivation.license_id == license_obj.id, LicenseActivation.status == "active")
        )
        if active_count and active_count >= max_devices:
            emit_event(db, "activation.blocked", "license", str(license_obj.id), {"reason": "device_limit"})
            raise HTTPException(status_code=403, detail="Device activation limit reached")
        device = Device(
            user_id=license_obj.user_id,
            machine_label=device_label,
            fingerprint_hash=fp_hash,
            fingerprint_version=fingerprint.version,
            fingerprint_components=fingerprint.model_dump(),
            confidence_score=100,
        )
        db.add(device)
        db.flush()

    activation = db.scalar(
        select(LicenseActivation).where(
            LicenseActivation.license_id == license_obj.id,
            LicenseActivation.device_id == device.id,
            LicenseActivation.deleted_at.is_(None),
        )
    )
    if not activation:
        activation = LicenseActivation(
            license_id=license_obj.id,
            device_id=device.id,
            app_version=app_version,
            ip_address=ip_address,
        )
        db.add(activation)
    activation.status = "active"
    activation.last_validated_at = datetime.now(UTC)
    detect_activation_abuse(db, license_obj.id, fp_hash)
    emit_event(db, "activation.created", "license", str(license_obj.id), {"device_id": str(device.id)})
    db.flush()
    return signed_license_payload(db, license_obj, product, device, activation)


def signed_license_payload(db: Session, license_obj: License, product: Product, device: Device, activation: LicenseActivation) -> dict:
    policy = license_obj.policy
    state = _license_state(license_obj)
    update_eligible = not license_obj.update_access_expires_at or license_obj.update_access_expires_at >= datetime.now(UTC)
    payload = {
        "valid": state == "active",
        "status": state,
        "license_id": str(license_obj.id),
        "license_key_tail": license_obj.key[-8:],
        "product": {"id": str(product.id), "slug": product.slug, "name": product.name},
        "device": {
            "id": str(device.id),
            "fingerprint_version": device.fingerprint_version,
            "confidence_score": device.confidence_score,
        },
        "activation_id": str(activation.id),
        "expires_at": license_obj.expires_at.isoformat() if license_obj.expires_at else None,
        "offline_valid_until": (datetime.now(UTC) + timedelta(days=policy.offline_days)).isoformat(),
        "revalidation_interval_hours": policy.revalidation_interval_hours,
        "expired_behavior": policy.expired_behavior,
        "update_eligible": update_eligible,
        "entitlements": _entitlements(db, license_obj),
        "minimum_backend_supported_app_version": product.min_backend_supported_version,
    }
    return sign_payload(payload, expires_in_seconds=policy.revalidation_interval_hours * 3600)


def validate_license(
    db: Session,
    license_key: str,
    product_slug: str,
    app_version: str,
    fingerprint: FingerprintInput,
) -> dict:
    license_obj, product = _load_license(db, license_key, product_slug)
    fp_hash = fingerprint_hash(fingerprint)
    device = db.scalar(select(Device).where(Device.fingerprint_hash == fp_hash, Device.user_id == license_obj.user_id))
    if not device:
        raise HTTPException(status_code=403, detail="Device is not activated")
    activation = db.scalar(
        select(LicenseActivation).where(
            LicenseActivation.license_id == license_obj.id,
            LicenseActivation.device_id == device.id,
            LicenseActivation.status == "active",
        )
    )
    if not activation:
        raise HTTPException(status_code=403, detail="Activation is not active")
    activation.last_validated_at = datetime.now(UTC)
    activation.app_version = app_version
    emit_event(db, "license.validated", "license", str(license_obj.id), {"device_id": str(device.id)})
    return signed_license_payload(db, license_obj, product, device, activation)
