from datetime import UTC, datetime, timedelta
from hashlib import sha256

from fastapi import HTTPException, status
from packaging.version import InvalidVersion, Version
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import generate_license_key
from app.core.signing import sign_payload
from app.db.models import (
    Device,
    Entitlement,
    ActivationRule,
    License,
    LicenseActivation,
    LicensePolicy,
    LicenseValidationNonce,
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


def _version_lt(left: str, right: str) -> bool:
    try:
        return Version(left) < Version(right)
    except InvalidVersion:
        return left < right


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _fingerprint_confidence(stored: dict, incoming: FingerprintInput) -> int:
    incoming_components = incoming.model_dump()
    score = 0
    if stored.get("app_installation_id") and stored.get("app_installation_id") == incoming_components.get("app_installation_id"):
        score += 40
    if stored.get("machine_id") and stored.get("machine_id") == incoming_components.get("machine_id"):
        score += 30
    if stored.get("os") and stored.get("os") == incoming_components.get("os"):
        score += 10
    if stored.get("cpu_hash") and stored.get("cpu_hash") == incoming_components.get("cpu_hash"):
        score += 10
    if stored.get("motherboard_hash") and stored.get("motherboard_hash") == incoming_components.get("motherboard_hash"):
        score += 10
    if not stored.get("machine_id") and stored.get("fallback_hash") and stored.get("fallback_hash") == incoming_components.get("fallback_hash"):
        score += 30
    return min(score, 100)


def _activation_rule(db: Session, policy_id) -> ActivationRule | None:
    return db.scalar(
        select(ActivationRule).where(
            ActivationRule.policy_id == policy_id,
            ActivationRule.deleted_at.is_(None),
        )
    )


def _find_tolerated_device(db: Session, license_obj: License, fingerprint: FingerprintInput) -> Device | None:
    policy = license_obj.policy
    rule = _activation_rule(db, policy.id)
    tolerance = rule.tolerance_score if rule else 80
    candidates = db.scalars(
        select(Device).where(
            Device.user_id == license_obj.user_id,
            Device.deleted_at.is_(None),
            Device.status == "active",
        )
    ).all()
    best_device = None
    best_score = 0
    for candidate in candidates:
        score = _fingerprint_confidence(candidate.fingerprint_components or {}, fingerprint)
        if score > best_score:
            best_device = candidate
            best_score = score
    if best_device and best_score >= tolerance:
        best_device.fingerprint_hash = fingerprint_hash(fingerprint)
        best_device.fingerprint_version = fingerprint.version
        best_device.fingerprint_components = fingerprint.model_dump()
        best_device.confidence_score = best_score
        return best_device
    return None


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
    expires_at = _as_utc(license_obj.expires_at)
    if expires_at and expires_at < now:
        return "expired"
    return license_obj.status


def is_license_usable(license_obj: License) -> bool:
    return _license_state(license_obj) == "active"


def record_validation_nonce(
    db: Session,
    nonce: str | None,
    license_id=None,
    device_id=None,
    ttl_seconds: int = 900,
) -> None:
    if not nonce:
        return
    existing = db.scalar(select(LicenseValidationNonce).where(LicenseValidationNonce.nonce == nonce))
    if existing:
        emit_event(db, "license.replay_rejected", "license", str(license_id) if license_id else None, {"nonce": nonce})
        raise HTTPException(status_code=409, detail="Replay nonce already used")
    db.add(
        LicenseValidationNonce(
            nonce=nonce,
            license_id=license_id,
            device_id=device_id,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )
    )
    db.flush()


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
    if state in {"revoked", "suspended", "blacklisted", "expired"}:
        raise HTTPException(status_code=403, detail=f"License is {state}")

    fp_hash = fingerprint_hash(fingerprint)
    policy: LicensePolicy = license_obj.policy
    max_devices = license_obj.max_devices_override or policy.max_devices

    device = db.scalar(select(Device).where(Device.fingerprint_hash == fp_hash, Device.user_id == license_obj.user_id))
    if not device:
        device = _find_tolerated_device(db, license_obj, fingerprint)
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
    update_access_expires_at = _as_utc(license_obj.update_access_expires_at)
    update_eligible = not update_access_expires_at or update_access_expires_at >= datetime.now(UTC)
    offline_days = policy.trial_offline_days if policy.license_type == "trial" or license_obj.source == "trial" else policy.offline_days
    app_compatible = not _version_lt(activation.app_version or "0.0.0", product.min_backend_supported_version)
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
        "offline_valid_until": None
        if state in {"revoked", "suspended", "blacklisted"}
        else (datetime.now(UTC) + timedelta(days=offline_days)).isoformat(),
        "revalidation_interval_hours": policy.revalidation_interval_hours,
        "expired_behavior": policy.expired_behavior,
        "update_eligible": update_eligible,
        "entitlements": _entitlements(db, license_obj),
        "minimum_backend_supported_app_version": product.min_backend_supported_version,
        "app_compatible": app_compatible,
        "force_upgrade": not app_compatible,
        "clock_tamper_hint": {"server_timestamp": int(datetime.now(UTC).timestamp())},
    }
    return sign_payload(payload, expires_in_seconds=policy.revalidation_interval_hours * 3600)


def validate_license(
    db: Session,
    license_key: str,
    product_slug: str,
    app_version: str,
    fingerprint: FingerprintInput,
    client_nonce: str | None = None,
) -> dict:
    license_obj, product = _load_license(db, license_key, product_slug)
    state = _license_state(license_obj)
    if state in {"revoked", "suspended", "blacklisted"}:
        raise HTTPException(status_code=403, detail=f"License is {state}")
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
    record_validation_nonce(db, client_nonce, license_obj.id, device.id)
    activation.last_validated_at = datetime.now(UTC)
    activation.app_version = app_version
    emit_event(db, "license.validated", "license", str(license_obj.id), {"device_id": str(device.id)})
    return signed_license_payload(db, license_obj, product, device, activation)
