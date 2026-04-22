from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

try:
    import boto3
except ImportError:  # Allows local static checks before dependencies are installed.
    boto3 = None

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.client = None
        if boto3 is None:
            return
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )

    def signed_get_url(self, bucket: str, object_key: str, ttl: int | None = None) -> str:
        if self.client is None:
            return f"http://localhost:9000/{bucket}/{object_key}?dev-signed=true"
        return self.client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=ttl or settings.signed_url_ttl_seconds,
        )

    def upload_bytes(self, bucket: str, object_key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        if self.client is None:
            target = Path(".local-storage") / bucket / object_key
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            return
        try:
            self.client.put_object(Bucket=bucket, Key=object_key, Body=data, ContentType=content_type)
        except Exception:
            if settings.app_env == "production":
                raise
            target = Path(".local-storage") / bucket / object_key
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)


def checksum_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def checksum_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def signed_url_expires_at() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=settings.signed_url_ttl_seconds)


storage_service = StorageService()
