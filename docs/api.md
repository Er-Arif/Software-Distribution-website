# API Documentation

Base path: `/api/v1`

## Auth

- `POST /auth/register`
- `POST /auth/login`

Auth endpoints use strict rate limits.

## Public

- `GET /public/products`
- `GET /public/products/{slug}`
- `GET /public/changelog`
- `GET /public/legal/{document_type}`

Public endpoints use relaxed rate limits.

## Desktop

- `GET /desktop/public-keys`
- `POST /desktop/licenses/activate`
- `POST /desktop/licenses/validate`
- `POST /desktop/licenses/heartbeat`
- `GET /desktop/updates/manifest`

Desktop endpoints use medium-strict rate limits and return signed license/update payloads.

## Downloads

- `GET /downloads/builds/{build_id}/signed-url`

Download endpoints use high-protection rate limits and require active entitlement checks.

## Admin

- `GET /admin/dashboard`
- `GET /admin/audit-logs`
- `GET /admin/events`
- `POST /admin/licenses/{license_id}/revoke?confirm=true`

Admin endpoints require RBAC. Critical mutations require explicit confirmation and audit logging.
