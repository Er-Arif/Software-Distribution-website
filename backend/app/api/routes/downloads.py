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

router = APIRouter(dependencies=[Depends(rate_limit("download"))])


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
    license_obj = db.scalar(
        select(License).where(
            License.user_id == user.id,
            License.product_id == version.product_id,
            License.status == "active",
            License.deleted_at.is_(None),
        )
    )
    if not license_obj:
        raise HTTPException(status_code=403, detail="No active entitlement for download")
    file_obj = db.get(FileMetadata, build.file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="File metadata missing")
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
