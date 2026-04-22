from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.core.rate_limit import rate_limit
from app.core.storage import signed_url_expires_at, storage_service
from app.db.models import BuildAsset, Download, FileMetadata, License, ProductVersion, User
from app.schemas import DownloadLink
from app.services.events import emit_event
from app.services.licensing import is_license_usable

router = APIRouter(dependencies=[Depends(rate_limit("download"))])


def _as_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@router.get("/builds/{build_id}/signed-url", response_model=DownloadLink)
def signed_download_url(
    build_id: UUID,
    request: Request,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> DownloadLink:
    build = db.get(BuildAsset, build_id)
    if not build or build.deleted_at:
        raise HTTPException(status_code=404, detail="Build not found")
    version = db.get(ProductVersion, build.product_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    if version.status != "published" or version.deleted_at:
        raise HTTPException(status_code=403, detail="Build is not published")
    license_obj = db.scalar(
        select(License).where(
            License.user_id == user.id,
            License.product_id == version.product_id,
            License.status == "active",
            License.deleted_at.is_(None),
        )
    )
    if not license_obj or not is_license_usable(license_obj):
        raise HTTPException(status_code=403, detail="No active entitlement for download")
    file_obj = db.get(FileMetadata, build.file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="File metadata missing")
    if file_obj.scan_status not in {"clean", "trusted"}:
        raise HTTPException(status_code=403, detail="File is not cleared for download")
    published_at = _as_utc(version.published_at)
    update_access_expires_at = _as_utc(license_obj.update_access_expires_at)
    if published_at and update_access_expires_at and published_at > update_access_expires_at:
        raise HTTPException(status_code=403, detail="Update access expired for this build")
    url = storage_service.signed_get_url(file_obj.bucket, file_obj.object_key)
    db.add(
        Download(
            user_id=user.id,
            product_id=license_obj.product_id,
            build_asset_id=build.id,
            license_id=license_obj.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            status="signed_url_created",
        )
    )
    emit_event(db, "download.completed", "build", str(build.id), {"user_id": str(user.id)})
    db.commit()
    return DownloadLink(url=url, expires_at=signed_url_expires_at(), checksum_sha256=build.checksum_sha256)
