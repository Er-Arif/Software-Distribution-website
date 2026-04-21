from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_user
from app.db.models import User
from app.schemas import CheckoutRequest, CheckoutResponse
from app.services.payments import create_checkout, record_webhook, verify_razorpay_webhook

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
    record_webhook(db, "razorpay", event_id, payload)
    db.commit()
    return {"received": True}
