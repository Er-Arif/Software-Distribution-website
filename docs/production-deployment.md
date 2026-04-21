# Production Deployment

## Required Production Changes

- Replace all secrets in `.env`.
- Use managed PostgreSQL with backups.
- Use managed Redis or hardened Redis.
- Use S3-compatible object storage with private buckets.
- Serve behind HTTPS reverse proxy.
- Configure CORS to the production frontend URL only.
- Configure Sentry or another error tracking provider.
- Configure transactional email provider.

## Secrets

Never commit real secrets. Use environment variables or a secret manager.

Required sensitive values:

- `JWT_SECRET`
- `LICENSE_PRIVATE_KEY_PEM`
- Razorpay secrets
- PayPal secrets
- S3 credentials
- SMTP credentials

## Health Checks

- `/api/v1/health`
- `/api/v1/health/ready`

Add external monitoring for API failures, webhook failures, worker failures, storage failures, and database connectivity.
