from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/software_platform"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = Field(default="change-me")
    jwt_access_minutes: int = 15
    jwt_refresh_days: int = 30

    signing_key_id: str = "local-dev-key"
    license_private_key_pem: str = ""
    license_public_key_pem: str = ""

    storage_backend: Literal["s3", "local"] = "s3"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_public_assets_bucket: str = "public-assets"
    s3_private_installers_bucket: str = "private-installers"
    s3_update_patches_bucket: str = "update-patches"
    signed_url_ttl_seconds: int = 300

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_webhook_id: str = ""

    sentry_dsn: str = ""
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
