from packaging.version import Version
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.signing import sign_payload
from app.db.models import BuildAsset, Product, ProductVersion, ReleaseNote


def latest_manifest(db: Session, product_slug: str, os: str, architecture: str, current_version: str) -> dict | None:
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
    build = db.scalar(
        select(BuildAsset).where(
            BuildAsset.product_version_id == latest.id,
            BuildAsset.os == os,
            BuildAsset.architecture == architecture,
            BuildAsset.deleted_at.is_(None),
        )
    )
    notes = db.scalars(select(ReleaseNote).where(ReleaseNote.product_version_id == latest.id)).all()
    force = latest.forced_update or Version(current_version) < Version(product.min_backend_supported_version)
    manifest = {
        "product": product.slug,
        "version": latest.version,
        "current_version": current_version,
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
