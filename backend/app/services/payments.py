import hmac
from hashlib import sha256

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Order, Payment, Plan, WebhookEvent
from app.services.events import emit_event


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
    payment = Payment(
        order_id=order.id,
        provider="razorpay",
        provider_order_id=f"local_order_{order.id}",
        amount=order.total_amount,
        currency=order.currency,
        status="created",
    )
    db.add(payment)
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
