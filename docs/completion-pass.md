# Strict Completion Pass

## Completed Core Flows

- Auth: registration, login, refresh-token rotation, role checks, account suspension checks.
- Licensing: manual/payment license creation, activation, validation, device limits, revocation blocking, expiry blocking, offline token fields, signed responses, replay nonce rejection.
- Payments: checkout order creation, order items, Razorpay/PayPal webhook processing, verified payment license issuance, invoices, failed payment handling, refunds, partial refunds, subscription grace.
- Downloads and updates: entitlement-protected signed download URLs, download logs/events, signed update manifests, compatibility force-upgrade checks, rollback fallback.
- Admin: operational read endpoints and create/safeguarded mutation endpoints for products, plans, policies, manual licenses, versions, builds, rollback, customers, orders, payments, support, legal content, audit, events, analytics.
- Customer portal: authenticated API-backed pages for dashboard, products, licenses, devices, downloads, billing, support, notifications, plus checkout/support/device actions through backend APIs.
- Support/events/audit: customer tickets, replies, staff replies, domain events separated from audit logs, notifications emitted for payment outcomes.

## Verified By Tests

Run from `backend/`:

```bash
python -B -m pytest tests -p no:cacheprovider
```

The suite covers auth/RBAC, license activation and validation, replay protection, payment-to-license issuance, refunds, subscription grace, downloads, update rollback, support events, admin operational CRUD/safeguards, and audit separation.

Frontend verification:

```bash
cd frontend
cmd /c npm run build
```

The frontend build generates public, customer, and admin routes.

## Pending Production Integrations

- Real Razorpay order creation API call and PayPal provider verification endpoint calls need live credentials.
- Installer upload, malware scanning, and platform code-signing invocation need production infrastructure.
- Admin screens are API-backed operational pages; richer form UX can be expanded screen by screen without changing the core APIs.
- Docker Compose config/build should be re-run after Docker Desktop Linux engine is running.

## Docker Verification

Compose config was previously valid. The latest backend image build could not run because Docker Desktop's Linux engine was stopped:

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

After starting Docker Desktop, run:

```bash
docker compose build backend
docker compose up --build -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```
