# Operations runbook

## First deployment

1. Create the database and application identity.
2. Set `.env` values using a secret manager.
3. Run `flask --app wsgi db upgrade`.
4. Create the first admin with the bootstrap command documented in the README.
5. Import the workbook in a non-production environment and review the validation summary.
6. Take a backup, then import into production.
7. Run smoke tests for all four roles and offline submission on a real mobile device.

## Scheduled jobs

Run `flask --app wsgi purge-recycle-bin` daily. It permanently deletes recycle-bin snapshots older
than the configured ten-day retention period. Export the audit log and database backup before
changing retention.

## Backups

Back up PostgreSQL daily with encrypted off-site retention. Back up photo storage using object versioning
or immutable snapshots. Keep migration files with each release. Quarterly, restore the database and
uploads into an isolated environment and verify row counts, image links, logins, and dashboards.

## Rollback

For an application-only failure, redeploy the previous image without reverting the database when the
migration is backward-compatible. Before schema changes, take a snapshot. For an incompatible
migration, stop writers, restore the snapshot and matching uploads, deploy the previous release, and
run scoped smoke tests. Never run destructive migration downgrades against production without a
tested backup.

## Observability

Log request IDs, role, route, status, latency, and sanitized entity IDs. Track login failures,
submission success/error counts, offline replay duplicates, image processing errors, DB latency,
HTTP 5xx rate, queue depth reported by clients, and purge counts. Alert on sustained 5xx errors,
database connection failures, disk/volume pressure, and stale backups.
