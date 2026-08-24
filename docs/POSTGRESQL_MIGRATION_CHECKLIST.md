# SQLite -> PostgreSQL Production Migration Checklist

This checklist is for the accepted local SQLite database moving into the Coolify PostgreSQL resource.

## Before migration

- PostgreSQL resource is private/internal and healthy.
- Application `DATABASE_URL` uses the Coolify PostgreSQL Internal URL.
- `flask --app wsgi db upgrade` completed successfully.
- Target application tables are empty.
- Accepted SQLite DB has a separate backup copy.
- Existing `/uploads` evidence directory has a separate backup.
- UAT-only temporary records are reviewed/removed or intentionally retained.

## Dry run

```bash
python scripts/migrate_sqlite_to_postgresql.py \
  --source /tmp/model_village.db \
  --dry-run
```

Check the source row counts before writing.

## Migration

```bash
python scripts/migrate_sqlite_to_postgresql.py \
  --source /tmp/model_village.db
```

The helper:
- refuses a non-PostgreSQL target;
- refuses non-empty target application tables;
- copies in dependency order;
- safely defers `ActionPlan.prepared_from_id` self-references;
- reseeds PostgreSQL serial/identity sequences after explicit SQLite IDs;
- commits the copy as one target transaction.

## After migration

Verify at minimum:
- PM = 2
- PC = 2
- DA = 9
- Village = 42
- Committee = 351
- Committee Member = 2,433

The counts above describe the original normalized program baseline. If legitimate production/UAT data
has been added since that baseline, compare against the accepted SQLite source counts instead of forcing
these historical numbers.

Then verify:
- Admin login
- PM global read
- PC scoped read + Action Plan export
- DA Attendance landing
- Reports
- Recycle Bin
- `/readyz`
- map rendering
- one controlled field submission

Copy evidence uploads separately into the persistent `/srv/app/uploads` volume if the SQLite installation
already contains field evidence files.
