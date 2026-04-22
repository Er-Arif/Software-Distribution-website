from datetime import UTC

from packaging.version import Version
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.signing import sign_payload
from app.db.models import BuildAsset, License, Product, ProductVersion, ReleaseNote
from app.services.licensing import is_license_usable


def _as_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _version(value: str) -> Version:
    return Version(value)


def latest_manifest(
    db: Session,
    product_slug: str,
    os: str,
    architecture: str,
    current_version: str,
    license_key: str | None = None,
) -> dict | None:
    product = db.scalar(select(Product).where(Product.slug == product_slug, Product.deleted_at.is_(None)))
    if not product:
        return None
    versions = db.scalars(
        select(ProductVersion)
        .where(
            ProductVersion.product_id == product.id,
            ProductVersion.status == "published",
            ProductVersion.deleted_at.is_(None),
        )
        .order_by(ProductVersion.published_at.desc().nullslast(), ProductVersion.created_at.desc())
    ).all()
    if not versions:
        return None
    latest = versions[0].rollback_to_version_id and db.get(ProductVersion, versions[0].rollback_to_version_id) or versions[0]
    license_obj = None
    if license_key:
        license_obj = db.scalar(
            select(License).where(
                License.key == license_key,
                License.product_id == product.id,
                License.deleted_at.is_(None),
            )
        )
    update_eligible = True
    if license_key and (not license_obj or not is_license_usable(license_obj)):
        update_eligible = False
    latest_published_at = _as_utc(latest.published_at)
    update_access_expires_at = _as_utc(license_obj.update_access_expires_at) if license_obj else None
    if license_obj and latest_published_at and update_access_expires_at and latest_published_at > update_access_expires_at:
        update_eligible = False
    build = db.scalar(
        select(BuildAsset).where(
            BuildAsset.product_version_id == latest.id,
            BuildAsset.os == os,
            BuildAsset.architecture == architecture,
            BuildAsset.deleted_at.is_(None),
        )
    )
    notes = db.scalars(select(ReleaseNote).where(ReleaseNote.product_version_id == latest.id)).all()
    force = latest.forced_update or _version(current_version) < _version(product.min_backend_supported_version)
    manifest = {
        "product": product.slug,
        "version": latest.version,
        "current_version": current_version,
        "update_available": _version(latest.version) != _version(current_version),
        "update_eligible": update_eligible,
        "force_update": force,
        "optional_update": latest.optional_update,
        "rollback_active": bool(versions[0].rollback_to_version_id),
        "build": None
        if not build
        else {
            "id": str(build.id),
            "os": build.os,
            "architecture": build.architecture,
            "installer_type": build.installer_type,
            "checksum_sha256": build.checksum_sha256,
            "code_signature_status": build.code_signature_status,
            "minimum_supported_version": build.minimum_supported_version,
        },
        "release_notes": [{"title": note.title, "body": note.body} for note in notes],
    }
    return sign_payload(manifest, expires_in_seconds=3600)
