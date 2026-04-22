from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.signing import verify_signed_payload
from app.core.config import settings
from app.core.totp import _hotp
from app.db.models import AuditLog, BuildAsset, DomainEvent, FileMetadata, InvoiceRecord, License, Order, Payment, ProductVersion, Subscription, SupportTicket
from app.schemas import FingerprintInput
from app.services.licensing import activate_license, validate_license
from app.services.payments import (
    apply_subscription_grace,
    create_checkout,
    process_payment_failed,
    process_payment_success,
    process_refund,
)
from app.services.updates import latest_manifest
from tests.factories import create_licensed_customer, create_product_graph, create_roles, create_user


def fp(name="device-1"):
    return FingerprintInput(os="windows", app_installation_id=name, machine_id=name)


def test_auth_refresh_rotation_rbac_and_suspension(client, db_session):
    create_roles(db_session)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "full_name": "New User", "password": "Password123!"},
    )
    assert response.status_code == 200
    refresh = response.json()["refresh_token"]

    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != refresh
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": refresh}).status_code == 401

    access = rotated.json()["access_token"]
    assert client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {access}"}).status_code == 403

    user = create_user(db_session, email="blocked@example.com", status="suspended")
    db_session.commit()
    blocked = client.post("/api/v1/auth/login", json={"email": user.email, "password": "Password123!"})
    assert blocked.status_code == 403


def test_license_activation_validation_device_limit_replay_and_revocation(db_session):
    _, product, _, _, license_obj, _, _ = create_licensed_customer(db_session, max_devices=1)
    signed = activate_license(db_session, license_obj.key, product.slug, "1.0.0", fp("device-1"), "Laptop", "127.0.0.1")
    assert verify_signed_payload(signed)
    assert signed["payload"]["valid"] is True
    assert signed["payload"]["entitlements"]["premium"]["enabled"] is True
    assert signed["payload"]["offline_valid_until"]

    valid = validate_license(db_session, license_obj.key, product.slug, "1.0.0", fp("device-1"), "nonce-1")
    assert verify_signed_payload(valid)
    replay = None
    try:
        validate_license(db_session, license_obj.key, product.slug, "1.0.0", fp("device-1"), "nonce-1")
    except Exception as exc:
        replay = exc
    assert replay is not None

    blocked = None
    try:
        activate_license(db_session, license_obj.key, product.slug, "1.0.0", fp("device-2"), "Desktop", "127.0.0.1")
    except Exception as exc:
        blocked = exc
    assert blocked is not None

    license_obj.status = "revoked"
    revoked = None
    try:
        validate_license(db_session, license_obj.key, product.slug, "1.0.0", fp("device-1"), "nonce-2")
    except Exception as exc:
        revoked = exc
    assert revoked is not None


def test_fingerprint_tolerance_and_compatibility_flags(db_session):
    _, product, _, _, license_obj, _, _ = create_licensed_customer(db_session, max_devices=1)
    product.min_backend_supported_version = "2.0.0"
    activate_license(
        db_session,
        license_obj.key,
        product.slug,
        "1.0.0",
        FingerprintInput(
            os="windows",
            app_installation_id="install-1",
            machine_id="machine-1",
            cpu_hash="cpu-old",
            motherboard_hash="board-1",
        ),
        "Laptop",
        "127.0.0.1",
    )
    tolerated = activate_license(
        db_session,
        license_obj.key,
        product.slug,
        "1.0.0",
        FingerprintInput(
            os="windows",
            app_installation_id="install-1",
            machine_id="machine-1",
            cpu_hash="cpu-new",
            motherboard_hash="board-1",
        ),
        "Laptop changed",
        "127.0.0.1",
    )
    assert verify_signed_payload(tolerated)
    assert tolerated["payload"]["force_upgrade"] is True
    assert tolerated["payload"]["app_compatible"] is False
    assert tolerated["payload"]["device"]["confidence_score"] >= 80


def test_expired_license_returns_signed_limited_state(db_session):
    _, product, _, _, license_obj, _, _ = create_licensed_customer(db_session)
    license_obj.expires_at = datetime.now(UTC) - timedelta(days=1)
    denied = None
    try:
        activate_license(db_session, license_obj.key, product.slug, "1.0.0", fp("expired"), "Old", "127.0.0.1")
    except Exception as exc:
        denied = exc
    assert denied is not None


def test_verified_payment_issues_license_invoice_and_is_idempotent(db_session):
    create_roles(db_session)
    user = create_user(db_session)
    _, plan, _, _, _ = create_product_graph(db_session)
    order, payment = create_checkout(db_session, user.id, plan.code)

    process_payment_success(db_session, payment.provider_order_id, "pay_1", {"subscription_id": "sub_1"})
    process_payment_success(db_session, payment.provider_order_id, "pay_1", {"subscription_id": "sub_1"})

    assert db_session.query(Payment).filter(Payment.status == "paid").count() == 1
    assert db_session.query(License).count() == 1
    assert db_session.query(InvoiceRecord).count() == 1
    assert db_session.query(InvoiceRecord).first().pdf_file_id is not None
    assert db_session.get(Order, order.id).status == "paid"

    subscription = db_session.query(Subscription).first()
    apply_subscription_grace(db_session, subscription.provider_subscription_id)
    assert subscription.status == "past_due"


def test_failed_payment_and_refund_paths(db_session):
    create_roles(db_session)
    user = create_user(db_session)
    _, plan, _, _, _ = create_product_graph(db_session)
    order, payment = create_checkout(db_session, user.id, plan.code)
    process_payment_failed(db_session, payment.provider_order_id, {"reason": "card_declined"})
    assert db_session.get(Order, order.id).status == "payment_failed"

    payment.status = "paid"
    payment.provider_payment_id = "pay_refund"
    db_session.flush()
    refund = process_refund(db_session, "pay_refund", 100, {"refund_id": "rfnd_1"}, partial=True)
    assert refund.status == "processed"
    assert payment.status == "partially_refunded"


def test_paypal_checkout_and_webhook_flow(client, db_session, monkeypatch):
    create_roles(db_session)
    user = create_user(db_session)
    _, plan, _, _, _ = create_product_graph(db_session)
    db_session.commit()
    token = client.post("/api/v1/auth/login", json={"email": user.email, "password": "Password123!"}).json()["access_token"]

    monkeypatch.setattr("app.services.payment_providers.paypal_client.create_order", lambda amount, currency, custom_id: f"pp_{custom_id}")
    monkeypatch.setattr("app.api.routes.payments.paypal_client.verify_webhook", lambda headers, payload: None)
    checkout = client.post(
        "/api/v1/payments/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json={"plan_code": plan.code, "provider": "paypal"},
    )
    assert checkout.status_code == 200
    provider_order_id = checkout.json()["provider_order_id"]
    webhook = client.post(
        "/api/v1/payments/webhooks/paypal",
        json={
            "id": "evt_pp_1",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {"id": "cap_1", "custom_id": provider_order_id},
        },
    )
    assert webhook.status_code == 200
    assert db_session.query(Payment).filter(Payment.provider == "paypal", Payment.status == "paid").count() == 1
    assert db_session.query(License).count() == 1


def test_download_update_rollback_support_and_audit(client, db_session):
    user, product, _, _, license_obj, version, build = create_licensed_customer(db_session)
    db_session.commit()
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "Password123!"})
    token = login.json()["access_token"]

    download = client.get(
        f"/api/v1/downloads/builds/{build.id}/signed-url",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert download.status_code == 200
    assert download.json()["checksum_sha256"] == "a" * 64
    available = client.get("/api/v1/customer/available-downloads", headers={"Authorization": f"Bearer {token}"})
    assert available.status_code == 200
    assert available.json()[0]["build_id"] == str(build.id)

    rollback = type(version)(
        product_id=product.id,
        version="0.9.0",
        status="published",
        published_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(rollback)
    db_session.flush()
    version.rollback_to_version_id = rollback.id
    manifest = latest_manifest(db_session, product.slug, "windows", "x64", "0.1.0", license_obj.key)
    assert verify_signed_payload(manifest)
    assert manifest["payload"]["rollback_active"] is True
    assert manifest["payload"]["version"] == "0.9.0"
    assert manifest["payload"]["update_eligible"] is True

    admin = create_user(db_session, email="admin@example.com", role_name="admin")
    db_session.commit()
    admin_login = client.post("/api/v1/auth/login", json={"email": admin.email, "password": "Password123!"})
    admin_token = admin_login.json()["access_token"]
    revoke = client.post(
        f"/api/v1/admin/licenses/{license_obj.id}/revoke?confirm=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert revoke.status_code == 200
    assert db_session.query(AuditLog).filter(AuditLog.action == "license.revoke").count() == 1


def test_download_blocks_unclean_files_expired_update_access_and_unpublished_builds(client, db_session):
    user, product, _, _, license_obj, version, build = create_licensed_customer(db_session)
    db_session.commit()
    token = client.post("/api/v1/auth/login", json={"email": user.email, "password": "Password123!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    version.status = "draft"
    db_session.commit()
    unpublished = client.get(f"/api/v1/downloads/builds/{build.id}/signed-url", headers=headers)
    assert unpublished.status_code == 403

    version.status = "published"
    file_obj = db_session.get(FileMetadata, build.file_id)
    file_obj.scan_status = "pending"
    db_session.commit()
    unclean = client.get(f"/api/v1/downloads/builds/{build.id}/signed-url", headers=headers)
    assert unclean.status_code == 403

    file_obj.scan_status = "clean"
    version.published_at = datetime.now(UTC)
    license_obj.update_access_expires_at = datetime.now(UTC) - timedelta(days=1)
    db_session.commit()
    expired_access = client.get(f"/api/v1/downloads/builds/{build.id}/signed-url", headers=headers)
    assert expired_access.status_code == 403


def test_support_notifications_events_are_separate(client, db_session):
    create_roles(db_session)
    user = create_user(db_session)
    db_session.commit()
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": "Password123!"})
    token = login.json()["access_token"]
    created = client.post(
        "/api/v1/support/tickets",
        headers={"Authorization": f"Bearer {token}"},
        json={"subject": "Activation help", "body": "I need help activating.", "priority": "high"},
    )
    assert created.status_code == 200
    ticket_id = created.json()["id"]
    reply = client.post(
        f"/api/v1/support/tickets/{ticket_id}/reply",
        headers={"Authorization": f"Bearer {token}"},
        json={"body": "Adding details."},
    )
    assert reply.status_code == 200
    assert db_session.query(DomainEvent).filter(DomainEvent.event_type == "support.ticket_created").count() == 1
    assert db_session.query(AuditLog).count() == 0


def test_admin_operational_crud_and_safeguards(client, db_session):
    create_roles(db_session)
    admin = create_user(db_session, email="ops@example.com", role_name="admin")
    user = create_user(db_session, email="buyer@example.com", role_name="customer")
    product, plan, policy, version, _ = create_product_graph(db_session)
    db_session.commit()
    token = client.post("/api/v1/auth/login", json={"email": admin.email, "password": "Password123!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    analytics = client.get("/api/v1/admin/analytics", headers=headers)
    assert analytics.status_code == 200
    assert "active_licenses" in analytics.json()

    policy_response = client.post(
        "/api/v1/admin/policies",
        headers=headers,
        json={"name": "Enterprise Offline", "license_type": "lifetime", "offline_days": 30, "max_devices": 10},
    )
    assert policy_response.status_code == 200

    license_response = client.post(
        "/api/v1/admin/licenses",
        headers=headers,
        json={
            "user_id": str(user.id),
            "product_id": str(product.id),
            "policy_id": str(policy.id),
            "plan_id": str(plan.id),
            "source": "manual",
        },
    )
    assert license_response.status_code == 200
    assert license_response.json()["key"].startswith("SW-")

    version_response = client.post(
        "/api/v1/admin/versions",
        headers=headers,
        json={"product_id": str(product.id), "version": "2.0.0", "status": "draft"},
    )
    assert version_response.status_code == 200
    new_version_id = version_response.json()["id"]

    build_response = client.post(
        "/api/v1/admin/builds",
        headers=headers,
        json={
            "product_version_id": new_version_id,
            "os": "windows",
            "architecture": "x64",
            "installer_type": "msi",
            "object_key": "codevault-pro/2.0.0/windows.msi",
            "size_bytes": 2048,
            "checksum_sha256": "b" * 64,
            "code_signature_status": "signed",
        },
    )
    assert build_response.status_code == 200
    created_build = db_session.get(BuildAsset, UUID(build_response.json()["id"]))
    db_session.get(FileMetadata, created_build.file_id).scan_status = "clean"
    db_session.commit()

    publish = client.post(f"/api/v1/admin/versions/{new_version_id}/publish?confirm=true", headers=headers)
    assert publish.status_code == 200
    fallback = db_session.query(ProductVersion).filter(ProductVersion.id == version.id).first()
    rollback = client.post(
        f"/api/v1/admin/versions/{new_version_id}/rollback?fallback_version_id={fallback.id}&confirm=true",
        headers=headers,
    )
    assert rollback.status_code == 200

    legal = client.post(
        "/api/v1/admin/legal",
        headers=headers,
        json={"document_type": "terms", "title": "Terms", "body": "Updated terms", "version": "2.0"},
    )
    assert legal.status_code == 200

    ticket = SupportTicket(user_id=user.id, product_id=product.id, subject="Help", priority="normal")
    db_session.add(ticket)
    db_session.commit()
    closed = client.post(f"/api/v1/admin/support-tickets/{ticket.id}/close", headers=headers)
    assert closed.status_code == 200
    assert db_session.query(AuditLog).filter(AuditLog.action.in_(["license.create", "release.rollback", "legal.publish", "support.close"])).count() >= 4


def test_admin_upload_scan_publish_and_2fa(client, db_session):
    create_roles(db_session)
    admin = create_user(db_session, email="secure-admin@example.com", role_name="admin")
    product, _, _, version, _ = create_product_graph(db_session)
    db_session.commit()
    token = client.post("/api/v1/auth/login", json={"email": admin.email, "password": "Password123!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    malware = client.post(
        f"/api/v1/admin/builds/upload?product_version_id={version.id}&os=windows&architecture=x64&installer_type=exe&code_signature_status=signed",
        headers=headers,
        files={"file": ("bad.exe", b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE", "application/octet-stream")},
    )
    assert malware.status_code == 200
    assert malware.json()["scan_status"] == "blocked"

    clean_version = ProductVersion(product_id=product.id, version="3.0.0", status="draft")
    db_session.add(clean_version)
    db_session.commit()
    uploaded = client.post(
        f"/api/v1/admin/builds/upload?product_version_id={clean_version.id}&os=windows&architecture=x64&installer_type=exe&code_signature_status=signed",
        headers=headers,
        files={"file": ("good.exe", b"installer-bytes", "application/octet-stream")},
    )
    assert uploaded.status_code == 200
    assert uploaded.json()["scan_status"] == "clean"
    publish = client.post(f"/api/v1/admin/versions/{clean_version.id}/publish?confirm=true", headers=headers)
    assert publish.status_code == 200

    setup = client.post("/api/v1/admin/2fa/setup", headers=headers)
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    code = _hotp(secret, int(__import__("time").time() // 30))
    enabled = client.post("/api/v1/admin/2fa/enable", headers=headers, json={"code": code})
    assert enabled.status_code == 200
    missing_code = client.post("/api/v1/auth/login", json={"email": admin.email, "password": "Password123!"})
    assert missing_code.status_code == 401
    with_code = client.post("/api/v1/auth/login", json={"email": admin.email, "password": "Password123!", "two_factor_code": code})
    assert with_code.status_code == 200
    assert db_session.query(AuditLog).filter(AuditLog.action.in_(["build.upload", "admin_2fa.enable"])).count() >= 2
