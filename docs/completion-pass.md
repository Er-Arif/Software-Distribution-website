# Strict Completion Pass

## Completed Core Flows

- Auth: registration, login, refresh-token rotation, role checks, account suspension checks.
- Licensing: manual/payment license creation, activation, validation, device limits, revocation blocking, expiry blocking, offline token fields, signed responses, replay nonce rejection.
- Payments: checkout order creation, order items, Razorpay/PayPal webhook processing, verified payment license issuance, invoices, failed payment handling, refunds, partial refunds, subscription grace.
- Downloads and updates: entitlement-protected signed download URLs, download logs/events, signed update manifests, compatibility force-upgrade checks, rollback fallback.
- Admin: operational read endpoints and create/safeguarded mutation endpoints for products, plans, policies, customers, licenses, orders, payments, versions, support, legal content, audit, events.
- Customer portal: authenticated API-backed pages for dashboard, products, licenses, devices, downloads, billing, support, notifications.
- Support/events/audit: customer tickets, replies, staff replies, domain events separated from audit logs, notifications emitted for payment outcomes.

## Verified By Tests

Run from `backend/`:

```bash
python -B -m pytest tests -p no:cacheprovider
```

The suite covers auth/RBAC, license activation and validation, replay protection, payment-to-license issuance, refunds, subscription grace, downloads, update rollback, support events, and audit separation.

## Pending Production Integrations

- Real Razorpay order creation API call and PayPal provider verification endpoint calls need live credentials.
- Installer upload, malware scanning, and platform code-signing invocation need production infrastructure.
- Admin forms are API-backed list pages plus core mutations; richer editing workflows can be expanded screen by screen.
- Docker Compose should be verified in the target machine after `.env` secrets and MinIO buckets are configured.
