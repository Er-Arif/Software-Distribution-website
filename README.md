# Software Distribution Platform

A production-oriented monorepo for selling, licensing, updating, and securely distributing desktop software.

## What Is Included

- Public software store built with Next.js, TypeScript, and Tailwind CSS.
- Customer portal for licenses, downloads, devices, billing, invoices, support, and notifications.
- Admin panel for products, builds, release workflows, customers, payments, licenses, devices, support, legal content, analytics, audit logs, and settings.
- FastAPI backend with PostgreSQL, Redis, Celery, Alembic, and MinIO-compatible storage.
- License server with device binding, entitlements, feature flags, offline tokens, policy rules, abuse detection, and asymmetric signing.
- Update server with signed manifests, release rollback, compatibility checks, channels, checksums, and platform-specific builds.
- Razorpay and PayPal payment architecture with strict webhook verification and invoice records.
- Documentation for setup, deployment, desktop integration, payments, backups, and roadmap.

## Quick Start

1. Copy `.env.example` to `.env` and replace secrets before real use.
2. Start services:

```bash
docker compose up --build
```

3. Run migrations and seed data:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

4. Open:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- MinIO console: http://localhost:9011
- Redis host port: `6380` maps to container port `6379`

If the frontend ever looks unstyled after local builds, restart the frontend container. Docker Compose keeps the container `.next` cache separate from the host to avoid Windows/Linux build-cache conflicts.

Default seed accounts:

- Admin: `admin@example.com` / `AdminPass123!`
- Customer: `customer@example.com` / `CustomerPass123!`

## Verification

With Docker running and seed data loaded:

```bash
cd frontend
npm run qa:api
npm run qa:browser
npm run build

cd ../backend
python -B -m pytest tests -p no:cacheprovider
```

The browser QA command launches Microsoft Edge/Chromium headlessly, visits public, customer, and admin routes, and fails on HTTP errors, missing stylesheets, console warnings/errors, page errors, or failed asset requests.

## Milestone Notes

Documentation should be updated with every implementation milestone. Git commits should be made after each meaningful update with clear messages.

See `docs/` for detailed architecture and operations guides.
