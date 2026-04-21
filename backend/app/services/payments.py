import hmac
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import InvoiceRecord, LicensePolicy, Order, OrderItem, Payment, Plan, RefundRecord, Subscription, WebhookEvent
from app.services.events import emit_event, notify
from app.services.licensing import create_manual_license


def create_checkout(db: Session, user_id, plan_code: str) -> tuple[Order, Payment]:
    plan = db.scalar(select(Plan).where(Plan.code == plan_code, Plan.status == "active"))
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    order = Order(
        user_id=user_id,
        subtotal_amount=plan.price_amount,
        total_amount=plan.price_amount,
        currency=plan.currency,
    )
    db.add(order)
    db.flush()
    db.add(
        OrderItem(
            order_id=order.id,
            product_id=plan.product_id,
            plan_id=plan.id,
            quantity=1,
            unit_amount=plan.price_amount,
        )
    )
    payment = Payment(
        order_id=order.id,
        provider="razorpay",
        provider_order_id=f"local_order_{order.id}",
        amount=order.total_amount,
        currency=order.currency,
        status="created",
    )
    db.add(payment)
    db.flush()
    emit_event(db, "order.created", "order", str(order.id), {"plan_code": plan_code})
    return order, payment


def verify_razorpay_webhook(body: bytes, signature: str | None) -> None:
    if not settings.razorpay_webhook_secret:
        return
    expected = hmac.new(settings.razorpay_webhook_secret.encode(), body, sha256).hexdigest()
    if not signature or not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")


def record_webhook(db: Session, provider: str, event_id: str, payload: dict) -> WebhookEvent:
    existing = db.scalar(select(WebhookEvent).where(WebhookEvent.provider == provider, WebhookEvent.event_id == event_id))
    if existing:
        return existing
    event = WebhookEvent(provider=provider, event_id=event_id, payload=payload)
    db.add(event)
    emit_event(db, "webhook.received", "webhook", event_id, {"provider": provider})
    return event


def process_payment_success(db: Session, provider_order_id: str, provider_payment_id: str, raw_payload: dict) -> Payment:
    payment = db.scalar(select(Payment).where(Payment.provider_order_id == provider_order_id))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found for provider order")
    if payment.status == "paid":
        return payment
    order = db.get(Order, payment.order_id)
    item = db.scalar(select(OrderItem).where(OrderItem.order_id == order.id))
    plan = db.get(Plan, item.plan_id)
    policy = db.scalar(select(LicensePolicy).where(LicensePolicy.license_type == plan.license_type, LicensePolicy.deleted_at.is_(None)))
    if not policy:
        policy = db.scalar(select(LicensePolicy).where(LicensePolicy.deleted_at.is_(None)))
    if not policy:
        raise HTTPException(status_code=500, detail="No license policy configured")

    payment.status = "paid"
    payment.provider_payment_id = provider_payment_id
    payment.verified_at = datetime.now(UTC)
    payment.raw_payload = raw_payload
    order.status = "paid"

    subscription = None
    expires_at = None
    if plan.license_type == "subscription":
        expires_at = datetime.now(UTC) + timedelta(days=365)
        subscription = Subscription(
            user_id=order.user_id,
            plan_id=plan.id,
            provider=payment.provider,
            provider_subscription_id=raw_payload.get("subscription_id"),
            status="active",
            current_period_end=expires_at,
        )
        db.add(subscription)
        db.flush()
    elif plan.license_type == "trial":
        expires_at = datetime.now(UTC) + timedelta(days=14)

    license_obj = create_manual_license(
        db,
        order.user_id,
        item.product_id,
        policy.id,
        source=payment.provider,
        expires_at=expires_at,
    )
    license_obj.plan_id = plan.id
    license_obj.order_id = order.id
    if subscription:
        license_obj.subscription_id = subscription.id
    if policy.update_access_days:
        license_obj.update_access_expires_at = datetime.now(UTC) + timedelta(days=policy.update_access_days)

    invoice = InvoiceRecord(
        order_id=order.id,
        payment_id=payment.id,
        invoice_number=f"INV-{str(order.id)[:8].upper()}",
        status="issued",
        total_amount=order.total_amount,
        tax_breakdown={"included": False, "tax_amount": float(order.tax_amount or 0)},
    )
    db.add(invoice)
    emit_event(db, "payment.succeeded", "payment", str(payment.id), {"order_id": str(order.id)})
    notify(db, order.user_id, "purchase_success", "Purchase complete", "Your license has been issued.", {"license_id": str(license_obj.id)})
    db.flush()
    return payment


def process_payment_failed(db: Session, provider_order_id: str, raw_payload: dict) -> Payment:
    payment = db.scalar(select(Payment).where(Payment.provider_order_id == provider_order_id))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found for provider order")
    payment.status = "failed"
    payment.raw_payload = raw_payload
    order = db.get(Order, payment.order_id)
    order.status = "payment_failed"
    emit_event(db, "payment.failed", "payment", str(payment.id), {"order_id": str(order.id)})
    notify(db, order.user_id, "payment_failed", "Payment failed", "Your payment could not be completed.", {})
    db.flush()
    return payment


def process_refund(db: Session, provider_payment_id: str, amount: float, raw_payload: dict, partial: bool = False) -> RefundRecord:
    payment = db.scalar(select(Payment).where(Payment.provider_payment_id == provider_payment_id))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found for refund")
    refund = RefundRecord(
        payment_id=payment.id,
        provider_refund_id=raw_payload.get("refund_id"),
        status="processed",
        amount=amount,
        currency=payment.currency,
        reason=raw_payload.get("reason"),
        raw_payload=raw_payload,
    )
    db.add(refund)
    payment.status = "partially_refunded" if partial else "refunded"
    emit_event(db, "payment.refunded", "payment", str(payment.id), {"partial": partial, "amount": amount})
    db.flush()
    return refund


def apply_subscription_grace(db: Session, provider_subscription_id: str) -> Subscription | None:
    subscription = db.scalar(select(Subscription).where(Subscription.provider_subscription_id == provider_subscription_id))
    if not subscription:
        return None
    plan = db.get(Plan, subscription.plan_id)
    policy = db.scalar(select(LicensePolicy).where(LicensePolicy.license_type == plan.license_type, LicensePolicy.deleted_at.is_(None)))
    grace_days = policy.grace_days_after_payment_failure if policy else 5
    subscription.status = "past_due"
    subscription.current_period_end = datetime.now(UTC) + timedelta(days=grace_days)
    emit_event(db, "subscription.grace_started", "subscription", str(subscription.id), {"grace_days": grace_days})
    return subscription
