from datetime import UTC, datetime, timedelta

from app.core.security import hash_password
from app.db.models import (
    AppUpdateChannel,
    ActivationRule,
    BuildAsset,
    Entitlement,
    FileMetadata,
    LicensePolicy,
    Plan,
    Product,
    ProductVersion,
    ReleaseNote,
    Role,
    User,
)
from app.services.licensing import create_manual_license


def create_roles(db):
    roles = {}
    for name in ["super_admin", "admin", "customer", "support"]:
        role = Role(name=name, description=name)
        db.add(role)
        roles[name] = role
    db.flush()
    return roles


def create_user(db, email="customer@example.com", role_name="customer", status="active"):
    role = db.query(Role).filter(Role.name == role_name).first() or Role(name=role_name, description=role_name)
    db.add(role)
    db.flush()
    user = User(
        email=email,
        full_name=email.split("@")[0],
        password_hash=hash_password("Password123!"),
        status=status,
        email_verified=True,
        roles=[role],
    )
    db.add(user)
    db.flush()
    return user


def create_product_graph(db, license_type="subscription", max_devices=2):
    product = Product(
        name="CodeVault Pro",
        slug="codevault-pro",
        tagline="Secure desktop vault",
        short_description="Short",
        long_description="Long",
        supported_os=["windows"],
        status="published",
    )
    db.add(product)
    db.flush()
    plan = Plan(
        product_id=product.id,
        name="Professional",
        code="codevault-pro",
        license_type=license_type,
        price_amount=2999,
        currency="INR",
        billing_interval="year",
    )
    policy = LicensePolicy(
        name="Policy",
        license_type=license_type,
        offline_days=7,
        update_access_days=365,
        max_devices=max_devices,
        revalidation_interval_hours=24,
    )
    channel = AppUpdateChannel(product_id=product.id, name="Stable", slug="stable", is_default=True)
    db.add_all([plan, policy, channel])
    db.flush()
    db.add(ActivationRule(policy_id=policy.id, tolerance_score=80))
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
        object_key="codevault-pro/1.0.0/windows.exe",
        visibility="private",
        mime_type="application/octet-stream",
        size_bytes=100,
        sha256="a" * 64,
        scan_status="clean",
    )
    db.add(file_meta)
    db.flush()
    build = BuildAsset(
        product_version_id=version.id,
        file_id=file_meta.id,
        os="windows",
        architecture="x64",
        installer_type="exe",
        checksum_sha256=file_meta.sha256,
        code_signature_status="signed",
    )
    db.add(build)
    db.add(ReleaseNote(product_version_id=version.id, title="Release", body="Ready"))
    db.add(Entitlement(product_id=product.id, plan_id=plan.id, feature_key="premium", value={"enabled": True}))
    db.flush()
    return product, plan, policy, version, build


def create_licensed_customer(db, max_devices=2):
    create_roles(db)
    user = create_user(db)
    product, plan, policy, version, build = create_product_graph(db, max_devices=max_devices)
    license_obj = create_manual_license(
        db,
        user.id,
        product.id,
        policy.id,
        source="test",
        expires_at=datetime.now(UTC) + timedelta(days=365),
    )
    license_obj.plan_id = plan.id
    license_obj.update_access_expires_at = datetime.now(UTC) + timedelta(days=365)
    db.flush()
    return user, product, plan, policy, license_obj, version, build
