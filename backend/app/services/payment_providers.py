import base64
import hmac
from hashlib import sha256

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


class RazorpayClient:
    base_url = "https://api.razorpay.com/v1"

    def create_order(self, amount: float, currency: str, receipt: str) -> str:
        if not settings.razorpay_key_id or not settings.razorpay_key_secret:
            return f"local_order_{receipt}"
        response = httpx.post(
            f"{self.base_url}/orders",
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
            json={"amount": int(round(amount * 100)), "currency": currency, "receipt": receipt},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["id"]

    def verify_webhook(self, body: bytes, signature: str | None) -> None:
        if not settings.razorpay_webhook_secret:
            if settings.app_env == "production":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Razorpay webhook secret missing")
            return
        expected = hmac.new(settings.razorpay_webhook_secret.encode(), body, sha256).hexdigest()
        if not signature or not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")


class PayPalClient:
    @property
    def base_url(self) -> str:
        return "https://api-m.paypal.com" if settings.paypal_environment == "live" else "https://api-m.sandbox.paypal.com"

    def _access_token(self) -> str:
        if not settings.paypal_client_id or not settings.paypal_client_secret:
            raise HTTPException(status_code=500, detail="PayPal credentials are not configured")
        encoded = base64.b64encode(f"{settings.paypal_client_id}:{settings.paypal_client_secret}".encode()).decode()
        response = httpx.post(
            f"{self.base_url}/v1/oauth2/token",
            headers={"Authorization": f"Basic {encoded}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def create_order(self, amount: float, currency: str, custom_id: str) -> str:
        if not settings.paypal_client_id or not settings.paypal_client_secret:
            return f"local_paypal_order_{custom_id}"
        token = self._access_token()
        response = httpx.post(
            f"{self.base_url}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [
                    {
                        "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
                        "custom_id": custom_id,
                    }
                ],
            },
            timeout=15,
        )
        response.raise_for_status()
        return response.json()["id"]

    def verify_webhook(self, headers: dict[str, str], payload: dict) -> None:
        if not settings.paypal_webhook_id:
            if settings.app_env == "production":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PayPal webhook ID missing")
            return
        token = self._access_token()
        response = httpx.post(
            f"{self.base_url}/v1/notifications/verify-webhook-signature",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "auth_algo": headers.get("paypal-auth-algo"),
                "cert_url": headers.get("paypal-cert-url"),
                "transmission_id": headers.get("paypal-transmission-id"),
                "transmission_sig": headers.get("paypal-transmission-sig"),
                "transmission_time": headers.get("paypal-transmission-time"),
                "webhook_id": settings.paypal_webhook_id,
                "webhook_event": payload,
            },
            timeout=15,
        )
        response.raise_for_status()
        if response.json().get("verification_status") != "SUCCESS":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PayPal webhook signature")


razorpay_client = RazorpayClient()
paypal_client = PayPalClient()
