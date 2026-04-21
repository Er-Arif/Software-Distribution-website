from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=10, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProductOut(BaseModel):
    id: UUID
    name: str
    slug: str
    tagline: str
    short_description: str
    supported_os: list[str]
    status: str

    class Config:
        from_attributes = True


class PlanOut(BaseModel):
    id: UUID
    name: str
    code: str
    license_type: str
    price_amount: float
    currency: str
    billing_interval: str | None

    class Config:
        from_attributes = True


class FingerprintInput(BaseModel):
    version: str = "v1"
    machine_id: str | None = None
    os: str
    os_version: str | None = None
    app_installation_id: str
    cpu_hash: str | None = None
    motherboard_hash: str | None = None
    fallback_hash: str | None = None


class LicenseActivateRequest(BaseModel):
    license_key: str
    product_slug: str
    app_version: str
    device_label: str | None = None
    fingerprint: FingerprintInput


class LicenseValidateRequest(BaseModel):
    license_key: str
    product_slug: str
    app_version: str
    fingerprint: FingerprintInput
    cached_token_nonce: str | None = None


class SignedResponse(BaseModel):
    payload: dict
    signature: str
    algorithm: str
    public_key_id: str


class CheckoutRequest(BaseModel):
    plan_code: str
    coupon_code: str | None = None
    billing_address_id: UUID | None = None


class CheckoutResponse(BaseModel):
    order_id: UUID
    provider: str
    provider_order_id: str
    amount: float
    currency: str


class DownloadLink(BaseModel):
    url: str
    expires_at: datetime
    checksum_sha256: str


class SupportTicketCreate(BaseModel):
    subject: str = Field(min_length=4, max_length=180)
    body: str = Field(min_length=4)
    product_id: UUID | None = None
    priority: str = "normal"


class AdminProductCreate(BaseModel):
    name: str
    slug: str
    tagline: str
    short_description: str
    long_description: str
    supported_os: list[str] = []
    status: str = "draft"


class AdminPlanCreate(BaseModel):
    product_id: UUID
    name: str
    code: str
    license_type: str = "subscription"
    price_amount: float
    currency: str = "INR"
    billing_interval: str | None = "year"
