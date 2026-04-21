from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def pk() -> Mapped[UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    id = pk()
    name: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255))


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    id = pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    roles: Mapped[list[Role]] = relationship(secondary=user_roles, lazy="selectin")


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"
    id = pk()
    user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProductCategory(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "product_categories"
    id = pk()
    name: Mapped[str] = mapped_column(String(120), unique=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)


class Product(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"
    id = pk()
    category_id = mapped_column(ForeignKey("product_categories.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    tagline: Mapped[str] = mapped_column(String(255))
    short_description: Mapped[str] = mapped_column(Text)
    long_description: Mapped[str] = mapped_column(Text)
    supported_os: Mapped[list[str]] = mapped_column(JSON, default=list)
    system_requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    min_backend_supported_version: Mapped[str] = mapped_column(String(40), default="1.0.0")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    category: Mapped[ProductCategory | None] = relationship()


class ProductImage(Base, TimestampMixin):
    __tablename__ = "product_images"
    id = pk()
    product_id = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    file_id = mapped_column(ForeignKey("file_metadata.id"), nullable=True)
    url: Mapped[str] = mapped_column(String(500))
    alt_text: Mapped[str] = mapped_column(String(255), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Plan(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "plans"
    id = pk()
    product_id = mapped_column(ForeignKey("products.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    license_type: Mapped[str] = mapped_column(String(30), default="subscription")
    price_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    billing_interval: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="active")


class LicensePolicy(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "license_policies"
    id = pk()
    name: Mapped[str] = mapped_column(String(140), unique=True)
    license_type: Mapped[str] = mapped_column(String(30))
    offline_days: Mapped[int] = mapped_column(Integer, default=7)
    trial_offline_days: Mapped[int] = mapped_column(Integer, default=3)
    grace_days_after_payment_failure: Mapped[int] = mapped_column(Integer, default=5)
    update_access_days: Mapped[int | None] = mapped_column(Integer)
    max_devices: Mapped[int] = mapped_column(Integer, default=1)
    revalidation_interval_hours: Mapped[int] = mapped_column(Integer, default=24)
    expired_behavior: Mapped[str] = mapped_column(String(30), default="limited")


class ActivationRule(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "activation_rules"
    id = pk()
    policy_id = mapped_column(ForeignKey("license_policies.id"), index=True)
    fingerprint_version: Mapped[str] = mapped_column(String(30), default="v1")
    tolerance_score: Mapped[int] = mapped_column(Integer, default=80)
    max_resets_per_year: Mapped[int] = mapped_column(Integer, default=3)
    suspicious_activation_window_minutes: Mapped[int] = mapped_column(Integer, default=60)
    suspicious_activation_count: Mapped[int] = mapped_column(Integer, default=5)


class FeatureFlag(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "feature_flags"
    id = pk()
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    scope: Mapped[str] = mapped_column(String(30), default="global")
    rules: Mapped[dict] = mapped_column(JSON, default=dict)


class Entitlement(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "entitlements"
    id = pk()
    product_id = mapped_column(ForeignKey("products.id"), nullable=True, index=True)
    plan_id = mapped_column(ForeignKey("plans.id"), nullable=True, index=True)
    license_id = mapped_column(ForeignKey("licenses.id"), nullable=True, index=True)
    user_id = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    feature_key: Mapped[str] = mapped_column(String(120), index=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Order(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "orders"
    id = pk()
    user_id = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    subtotal_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="INR")


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"
    id = pk()
    order_id = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id = mapped_column(ForeignKey("products.id"), index=True)
    plan_id = mapped_column(ForeignKey("plans.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_amount: Mapped[float] = mapped_column(Numeric(12, 2))


class BillingAddress(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "billing_addresses"
    id = pk()
    user_id = mapped_column(ForeignKey("users.id"), index=True)
    legal_name: Mapped[str] = mapped_column(String(180))
    line1: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(120))
    postal_code: Mapped[str] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(2), default="IN")
    gstin: Mapped[str | None] = mapped_column(String(20))


class TaxProfile(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tax_profiles"
    id = pk()
    name: Mapped[str] = mapped_column(String(140))
    country: Mapped[str] = mapped_column(String(2), default="IN")
    tax_name: Mapped[str] = mapped_column(String(40), default="GST")
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=18)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    id = pk()
    order_id = mapped_column(ForeignKey("orders.id"), index=True)
    provider: Mapped[str] = mapped_column(String(30), index=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(160), index=True)
    provider_order_id: Mapped[str | None] = mapped_column(String(160), index=True)
    status: Mapped[str] = mapped_column(String(30), default="created", index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)


class InvoiceRecord(Base, TimestampMixin):
    __tablename__ = "invoice_records"
    id = pk()
    order_id = mapped_column(ForeignKey("orders.id"), index=True)
    payment_id = mapped_column(ForeignKey("payments.id"), nullable=True)
    invoice_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    tax_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    pdf_file_id = mapped_column(ForeignKey("file_metadata.id"), nullable=True)


class Subscription(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "subscriptions"
    id = pk()
    user_id = mapped_column(ForeignKey("users.id"), index=True)
    plan_id = mapped_column(ForeignKey("plans.id"), index=True)
    provider: Mapped[str | None] = mapped_column(String(30))
    provider_subscription_id: Mapped[str | None] = mapped_column(String(160), index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class License(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "licenses"
    id = pk()
    user_id = mapped_column(ForeignKey("users.id"), index=True)
    product_id = mapped_column(ForeignKey("products.id"), index=True)
    plan_id = mapped_column(ForeignKey("plans.id"), nullable=True, index=True)
    policy_id = mapped_column(ForeignKey("license_policies.id"), index=True)
    subscription_id = mapped_column(ForeignKey("subscriptions.id"), nullable=True, index=True)
    order_id = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(30), default="payment")
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    update_access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_devices_override: Mapped[int | None] = mapped_column(Integer)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy: Mapped[LicensePolicy] = relationship()


class Device(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "devices"
    id = pk()
    user_id = mapped_column(ForeignKey("users.id"), index=True)
    machine_label: Mapped[str | None] = mapped_column(String(160))
    fingerprint_hash: Mapped[str] = mapped_column(String(128), index=True)
    fingerprint_version: Mapped[str] = mapped_column(String(30), default="v1")
    fingerprint_components: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence_score: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String(30), default="active")


class LicenseActivation(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "license_activations"
    id = pk()
    license_id = mapped_column(ForeignKey("licenses.id"), index=True)
    device_id = mapped_column(ForeignKey("devices.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    app_version: Mapped[str | None] = mapped_column(String(40))
    ip_address: Mapped[str | None] = mapped_column(String(80))


class FileMetadata(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "file_metadata"
    id = pk()
    bucket: Mapped[str] = mapped_column(String(120), index=True)
    object_key: Mapped[str] = mapped_column(String(500), index=True)
    visibility: Mapped[str] = mapped_column(String(30), default="private")
    mime_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    scan_status: Mapped[str] = mapped_column(String(30), default="pending")
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("bucket", "object_key", name="uq_file_bucket_key"),)


class AppUpdateChannel(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "app_update_channels"
    id = pk()
    product_id = mapped_column(ForeignKey("products.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(80), index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class ProductVersion(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "product_versions"
    id = pk()
    product_id = mapped_column(ForeignKey("products.id"), index=True)
    version: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    release_channel_id = mapped_column(ForeignKey("app_update_channels.id"), nullable=True)
    forced_update: Mapped[bool] = mapped_column(Boolean, default=False)
    optional_update: Mapped[bool] = mapped_column(Boolean, default=True)
    rollback_to_version_id = mapped_column(ForeignKey("product_versions.id"), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("product_id", "version", name="uq_product_version"),)


class BuildAsset(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "build_assets"
    id = pk()
    product_version_id = mapped_column(ForeignKey("product_versions.id"), index=True)
    file_id = mapped_column(ForeignKey("file_metadata.id"), nullable=True)
    os: Mapped[str] = mapped_column(String(30), index=True)
    architecture: Mapped[str] = mapped_column(String(30), index=True)
    installer_type: Mapped[str] = mapped_column(String(30))
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    code_signature_status: Mapped[str] = mapped_column(String(30), default="unsigned")
    signature_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    minimum_supported_version: Mapped[str] = mapped_column(String(40), default="1.0.0")


class ReleaseNote(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "release_notes"
    id = pk()
    product_version_id = mapped_column(ForeignKey("product_versions.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(30), default="public")


class Download(Base, TimestampMixin):
    __tablename__ = "downloads"
    id = pk()
    user_id = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    product_id = mapped_column(ForeignKey("products.id"), index=True)
    build_asset_id = mapped_column(ForeignKey("build_assets.id"), nullable=True)
    license_id = mapped_column(ForeignKey("licenses.id"), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(80))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="started")


class Coupon(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "coupons"
    id = pk()
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    discount_type: Mapped[str] = mapped_column(String(30), default="percent")
    discount_value: Mapped[float] = mapped_column(Numeric(8, 2))
    status: Mapped[str] = mapped_column(String(30), default="active")


class SupportTicket(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "support_tickets"
    id = pk()
    user_id = mapped_column(ForeignKey("users.id"), index=True)
    product_id = mapped_column(ForeignKey("products.id"), nullable=True)
    subject: Mapped[str] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    priority: Mapped[str] = mapped_column(String(30), default="normal")


class TicketMessage(Base, TimestampMixin):
    __tablename__ = "ticket_messages"
    id = pk()
    ticket_id = mapped_column(ForeignKey("support_tickets.id", ondelete="CASCADE"), index=True)
    author_id = mapped_column(ForeignKey("users.id"), index=True)
    body: Mapped[str] = mapped_column(Text)
    attachments: Mapped[list[dict]] = mapped_column(JSON, default=list)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    id = pk()
    user_id = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"
    id = pk()
    actor_id = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    target_type: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str | None] = mapped_column(String(80))
    ip_address: Mapped[str | None] = mapped_column(String(80))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class DomainEvent(Base, TimestampMixin):
    __tablename__ = "domain_events"
    id = pk()
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(80))
    aggregate_id: Mapped[str | None] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LegalDocument(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "legal_documents"
    id = pk()
    document_type: Mapped[str] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(40), default="1.0")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApiKey(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "api_keys"
    id = pk()
    user_id = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    key_hash: Mapped[str] = mapped_column(String(128), unique=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WebhookEvent(Base, TimestampMixin):
    __tablename__ = "webhook_events"
    id = pk()
    provider: Mapped[str] = mapped_column(String(30), index=True)
    event_id: Mapped[str] = mapped_column(String(180), index=True)
    status: Mapped[str] = mapped_column(String(30), default="received")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_provider_event"),)


Index("ix_license_product_user_status", License.product_id, License.user_id, License.status)
Index("ix_build_os_arch", BuildAsset.os, BuildAsset.architecture)
