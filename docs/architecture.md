# Architecture

The platform is split into a Next.js frontend, FastAPI backend, PostgreSQL database, Redis job broker, Celery workers, and S3-compatible object storage.

## Main Domains

- Commerce: orders, payments, subscriptions, refunds, invoices, tax profiles.
- Licensing: license policies, activation rules, licenses, devices, activations, entitlements, feature flags.
- Distribution: file metadata, private installers, signed URLs, download logs.
- Updates: product versions, platform builds, channels, release notes, signed manifests, rollback fallback.
- Operations: audit logs, domain events, notifications, support tickets, legal documents, API keys.

## Security Boundaries

- The server is the source of truth for licenses and entitlements.
- Desktop apps trust only signed server responses.
- Installers and update payloads are private unless a short-lived signed URL is issued after permission checks.
- Admin critical actions require confirmation and are audit logged.
