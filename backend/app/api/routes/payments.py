from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.db.models import User
from app.schemas import CheckoutRequest, CheckoutResponse
from app.services.payments import (
    apply_subscription_grace,
    create_checkout,
    process_payment_failed,
    process_payment_success,
    process_refund,
    record_webhook,
    verify_razorpay_webhook,
)

router = APIRouter()


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(payload: CheckoutRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> CheckoutResponse:
    order, payment = create_checkout(db, user.id, payload.plan_code)
    db.commit()
    return CheckoutResponse(
        order_id=order.id,
        provider=payment.provider,
        provider_order_id=payment.provider_order_id or "",
        amount=float(payment.amount),
        currency=payment.currency,
    )


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    body = await request.body()
    verify_razorpay_webhook(body, x_razorpay_signature)
    payload = await request.json()
    event_id = payload.get("event") + ":" + payload.get("created_at", "local")
    webhook = record_webhook(db, "razorpay", event_id, payload)
    if webhook.status == "received":
        event_name = payload.get("event")
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        if event_name == "payment.captured":
            process_payment_success(
                db,
                entity.get("order_id"),
                entity.get("id"),
                {"provider": "razorpay", **payload},
            )
        elif event_name == "payment.failed":
            process_payment_failed(db, entity.get("order_id"), {"provider": "razorpay", **payload})
        elif event_name == "refund.processed":
            refund = payload.get("payload", {}).get("refund", {}).get("entity", {})
            process_refund(
                db,
                refund.get("payment_id"),
                float(refund.get("amount", 0)) / 100,
                {"provider": "razorpay", "refund_id": refund.get("id"), **payload},
                partial=bool(refund.get("amount") and entity.get("amount") and refund.get("amount") < entity.get("amount")),
            )
        webhook.status = "processed"
    db.commit()
    return {"received": True}


@router.post("/webhooks/paypal")
async def paypal_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request.json()
    event_id = payload.get("id", "paypal-local")
    webhook = record_webhook(db, "paypal", event_id, payload)
    if webhook.status == "received":
        event_type = payload.get("event_type")
        resource = payload.get("resource", {})
        if event_type in {"CHECKOUT.ORDER.APPROVED", "PAYMENT.CAPTURE.COMPLETED"}:
            process_payment_success(
                db,
                resource.get("custom_id") or resource.get("invoice_id"),
                resource.get("id"),
                {"provider": "paypal", **payload},
            )
        elif event_type in {"PAYMENT.CAPTURE.DENIED", "BILLING.SUBSCRIPTION.PAYMENT.FAILED"}:
            provider_order_id = resource.get("custom_id") or resource.get("invoice_id")
            if provider_order_id:
                process_payment_failed(db, provider_order_id, {"provider": "paypal", **payload})
            if resource.get("billing_agreement_id"):
                apply_subscription_grace(db, resource["billing_agreement_id"])
        webhook.status = "processed"
    db.commit()
    return {"received": True}
