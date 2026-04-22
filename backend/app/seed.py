from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.db.base import Base
from app.db.models import (
    AppUpdateChannel,
    BuildAsset,
    Entitlement,
    FeatureFlag,
    FileMetadata,
    LegalDocument,
    LicensePolicy,
    Plan,
    Product,
    ProductCategory,
    ProductVersion,
    ReleaseNote,
    Role,
    User,
)
from app.services.licensing import create_manual_license


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == "admin@example.com")):
            db.query(FileMetadata).filter(FileMetadata.object_key.like("%/1.0.0/%"), FileMetadata.scan_status == "pending").update(
                {"scan_status": "clean"},
                synchronize_session=False,
            )
            db.commit()
            return
        roles = {
            name: Role(name=name, description=name.replace("_", " ").title())
            for name in ["super_admin", "admin", "customer", "support"]
        }
        db.add_all(roles.values())
        db.flush()
        admin = User(
            email="admin@example.com",
            full_name="Platform Admin",
            password_hash=hash_password("AdminPass123!"),
            email_verified=True,
            roles=[roles["super_admin"]],
        )
        customer = User(
            email="customer@example.com",
            full_name="Sample Customer",
            password_hash=hash_password("CustomerPass123!"),
            email_verified=True,
            roles=[roles["customer"]],
        )
        db.add_all([admin, customer])
        category = ProductCategory(name="Desktop Productivity", slug="desktop-productivity")
        db.add(category)
        db.flush()

        products = [
            Product(
                category_id=category.id,
                name="CodeVault Pro",
                slug="codevault-pro",
                tagline="Secure desktop vault for developer secrets.",
                short_description="Manage encrypted snippets, keys, and developer notes.",
                long_description="A premium encrypted desktop vault with licensing and secure updates.",
                supported_os=["windows", "macos", "linux"],
                status="published",
            ),
            Product(
                category_id=category.id,
                name="InvoiceForge",
                slug="invoiceforge",
                tagline="Offline-first invoices for small businesses.",
                short_description="Create GST-ready invoices from a polished desktop app.",
                long_description="InvoiceForge combines local desktop speed with cloud license validation.",
                supported_os=["windows", "macos"],
                status="published",
            ),
            Product(
                category_id=category.id,
                name="MediaBatch Studio",
                slug="mediabatch-studio",
                tagline="Batch media conversion with safe update channels.",
                short_description="Convert, resize, and automate media jobs on desktop.",
                long_description="A desktop media automation suite with beta channels and signed updates.",
                supported_os=["windows", "linux"],
                status="published",
            ),
        ]
        db.add_all(products)
        db.flush()

        policy = LicensePolicy(
            name="Standard Paid Policy",
            license_type="subscription",
            offline_days=7,
            update_access_days=365,
            max_devices=2,
        )
        trial_policy = LicensePolicy(name="Trial Policy", license_type="trial", offline_days=3, max_devices=1)
        db.add_all([policy, trial_policy])
        db.flush()

        for product in products:
            plan = Plan(
                product_id=product.id,
                name="Professional",
                code=f"{product.slug}-pro",
                license_type="subscription",
                price_amount=2999,
                currency="INR",
                billing_interval="year",
            )
            channel = AppUpdateChannel(product_id=product.id, name="Stable", slug="stable", is_default=True)
            db.add_all([plan, channel])
            db.flush()
            version = ProductVersion(
                product_id=product.id,
                version="1.0.0",
                status="published",
                release_channel_id=channel.id,
                published_at=datetime.now(UTC),
            )
            db.add(version)
            db.flush()
            file_meta = FileMetadata(
                bucket="private-installers",
                object_key=f"{product.slug}/1.0.0/windows-x64.exe",
                mime_type="application/octet-stream",
                size_bytes=1024,
                sha256="0" * 64,
                visibility="private",
                scan_status="clean",
            )
            db.add(file_meta)
            db.flush()
            db.add(
                BuildAsset(
                    product_version_id=version.id,
                    file_id=file_meta.id,
                    os="windows",
                    architecture="x64",
                    installer_type="exe",
                    checksum_sha256=file_meta.sha256,
                    code_signature_status="signed",
                )
            )
            db.add(ReleaseNote(product_version_id=version.id, title="Initial release", body="First stable release."))
            db.add(Entitlement(product_id=product.id, plan_id=plan.id, feature_key="premium_features", value={"enabled": True}))

        db.add_all(
            [
                FeatureFlag(key="beta_updates", name="Beta Updates", enabled=False, scope="product"),
                FeatureFlag(key="admin_impersonation", name="Admin Impersonation", enabled=True, scope="global"),
                LegalDocument(document_type="terms", title="Terms and Conditions", body="Initial terms.", published_at=datetime.now(UTC)),
                LegalDocument(document_type="privacy", title="Privacy Policy", body="Initial privacy policy.", published_at=datetime.now(UTC)),
                LegalDocument(document_type="refund", title="Refund Policy", body="Initial refund policy.", published_at=datetime.now(UTC)),
                LegalDocument(document_type="eula", title="License Agreement", body="Initial EULA.", published_at=datetime.now(UTC)),
            ]
        )
        db.flush()
        create_manual_license(db, customer.id, products[0].id, policy.id, source="seed", expires_at=datetime.now(UTC) + timedelta(days=365))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
