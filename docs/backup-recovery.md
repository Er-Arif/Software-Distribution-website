# Backup And Recovery

## Database Backups

- Run automated daily PostgreSQL backups.
- Keep point-in-time recovery enabled for production.
- Store backups in a separate protected bucket/account.
- Test restore at least monthly.

## File Storage Backups

Back up:

- Private installers.
- Update patches.
- Invoice PDFs.
- Legal document exports if required.

Public assets are easier to regenerate but should still be backed up.

## Restore Process

1. Freeze writes if the current system is still running.
2. Restore PostgreSQL to the target timestamp.
3. Restore object storage buckets.
4. Run migration rollback or forward migration as needed.
5. Verify health checks, license validation, signed downloads, and update manifest generation.

## Migration Rollback

Every production migration should include a tested rollback or a documented forward-fix strategy.
