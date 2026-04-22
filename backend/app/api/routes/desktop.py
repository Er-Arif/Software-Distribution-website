from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.signing import public_key_pem
from app.schemas import LicenseActivateRequest, LicenseValidateRequest
from app.services.licensing import activate_license, validate_license
from app.services.updates import latest_manifest

router = APIRouter(dependencies=[Depends(rate_limit("license"))])


@router.get("/public-keys")
def public_keys() -> dict:
    return {"keys": [{"kid": "local-dev-key", "pem": public_key_pem(), "status": "active"}]}


@router.post("/licenses/activate")
def activate(payload: LicenseActivateRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    ip = request.client.host if request.client else None
    signed = activate_license(
        db,
        payload.license_key,
        payload.product_slug,
        payload.app_version,
        payload.fingerprint,
        payload.device_label,
        ip,
    )
    db.commit()
    return signed


@router.post("/licenses/validate")
def validate(payload: LicenseValidateRequest, db: Session = Depends(get_db)) -> dict:
    signed = validate_license(
        db,
        payload.license_key,
        payload.product_slug,
        payload.app_version,
        payload.fingerprint,
        payload.cached_token_nonce,
    )
    db.commit()
    return signed


@router.post("/licenses/heartbeat")
def heartbeat(payload: LicenseValidateRequest, db: Session = Depends(get_db)) -> dict:
    signed = validate_license(
        db,
        payload.license_key,
        payload.product_slug,
        payload.app_version,
        payload.fingerprint,
        payload.cached_token_nonce,
    )
    db.commit()
    return signed


@router.get("/updates/manifest")
def update_manifest(
    product_slug: str,
    os: str,
    architecture: str,
    current_version: str,
    license_key: str | None = None,
    db: Session = Depends(get_db),
):
    return latest_manifest(db, product_slug, os, architecture, current_version, license_key) or {"update_available": False}
