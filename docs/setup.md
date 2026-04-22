# Setup Guide

## Prerequisites

- Docker and Docker Compose
- Node.js 22 if running frontend outside Docker
- Python 3.12 if running backend outside Docker

## Local Setup

```bash
cp .env.example .env
docker compose up --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

Services:

- Frontend: http://localhost:3000
- API: http://localhost:8000/docs
- MinIO: http://localhost:9011
- Redis: host port `6380`, container/service port `6379`

The frontend container uses its own `.next` cache volume. This prevents stale host build artifacts from breaking CSS or Next.js chunks inside Docker.

## Local Verification

Run these checks after changing routes, API contracts, auth, or dashboard behavior:

```bash
cd frontend
npm run qa:api
npm run qa:browser
npm run build

cd ../backend
python -B -m pytest tests -p no:cacheprovider
```

The API QA script verifies public, customer, and admin endpoints against the running backend. The browser QA script uses a real headless browser session, checks all main public/customer/admin pages, and fails on console errors, failed requests, missing CSS, or bad HTTP responses.

## Seed Accounts

- Admin: `admin@example.com` / `AdminPass123!`
- Customer: `customer@example.com` / `CustomerPass123!`

## Buckets

Create these buckets in MinIO for local development:

- `public-assets`
- `private-installers`
- `update-patches`

Production deployments should use equivalent S3-compatible buckets with least-privilege IAM credentials.
