# Payments And Billing

Razorpay is the primary India-friendly provider. PayPal is available as a secondary provider.

## Supported Flows

- One-time payment.
- Subscription payment.
- Failed payment and retry.
- Grace period after failed renewal.
- Refund and partial refund tracking.
- Invoice generation.

## Webhooks

Webhook verification must be strict in production:

- Razorpay uses HMAC SHA-256 verification.
- PayPal should verify against the provider webhook verification endpoint.
- Webhook events are stored idempotently with provider and event ID.
- Webhook processing should happen in background jobs for reliability.

## GST-Ready Data

The schema includes:

- `billing_addresses`
- `invoice_records`
- `tax_profiles`
