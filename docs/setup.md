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
- MinIO: http://localhost:9001

## Seed Accounts

- Admin: `admin@example.com` / `AdminPass123!`
- Customer: `customer@example.com` / `CustomerPass123!`

## Buckets

Create these buckets in MinIO for local development:

- `public-assets`
- `private-installers`
- `update-patches`

Production deployments should use equivalent S3-compatible buckets with least-privilege IAM credentials.
