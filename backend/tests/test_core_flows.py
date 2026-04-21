from datetime import UTC, datetime, timedelta

from app.core.signing import verify_signed_payload
from app.db.models import AuditLog, DomainEvent, InvoiceRecord, License, Order, Payment, Subscription
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

    rollback = type(version)(
        product_id=product.id,
        version="0.9.0",
        status="published",
        published_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(rollback)
    db_session.flush()
    version.rollback_to_version_id = rollback.id
    manifest = latest_manifest(db_session, product.slug, "windows", "x64", "0.1.0")
    assert verify_signed_payload(manifest)
    assert manifest["payload"]["rollback_active"] is True
    assert manifest["payload"]["version"] == "0.9.0"

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
    assert db_session.query(DomainEvent).filter(DomainEvent.event_type == "support.ticket_created").count() == 1
    assert db_session.query(AuditLog).count() == 0
