# Validation Report — 2026.27.3

Date: 2026-08-22

## Passed in the build environment

- Python source bytecode compilation: PASS
- Jinja template syntax: PASS — 16 templates
- JavaScript syntax via Node: PASS — 17 files
- PWA manifest JSON/standalone contract: PASS
- Touch-target/adaptive-breakpoint source contracts: PASS
- Centralized role scoping source contract: PASS
- IndexedDB outbox + Background Sync source contract: PASS
- WebP camera compression/geolocation source contract: PASS
- Attendance status/reason/idempotency source contract: PASS
- System-derived Failure projection source contract: PASS
- Monthly planning Export → Preview → Confirm source contract: PASS
- Prepare Next Month source contract: PASS
- Admin master-data Export → Preview → Confirm source contract: PASS
- Report Committee Member Name/View-detail source contract: PASS
- Admin move/recycle lifecycle source contract: PASS
- Leaflet/Three.js/Plotly Dash integration source contracts: PASS
- Alembic fresh SQLite upgrade: PASS — 13 domain/auth/audit tables
- Existing normalized SQLite seed → new migration: PASS
- Seed preservation after migration:
  - PMs 2
  - PCs 2
  - DAs 9
  - Villages 42
  - Committees 351
  - Committee Members 2,433
  - Legacy ActionPlan templates 351
- Bundled normalized workbook mapping: PASS
- Real normalized workbook entity counts: PASS
  - 2 / 2 / 9 / 42 / 351 / 2,433 / 351
- Approved prototype village-coordinate mapping: 42 records bundled.

## Runtime tests not executed in this build sandbox

The sandbox used to assemble this release does not contain the Flask runtime packages and has no
network access to install them. Therefore the full Flask application and pytest suite were not
executed here.

This is a release candidate until the following pass in the user's local virtual environment:

```powershell
python -m flask --app wsgi db upgrade
python -m flask --app wsgi backfill-village-coordinates
python -m pytest
python -m ruff check .
python -m flask --app wsgi run --debug
```

If Node is installed:

```powershell
Get-ChildItem .\app\static\js\*.js | ForEach-Object { node --check $_.FullName }
node --check .\app\static\sw.js
```

## Highest-value manual acceptance pass

1. Admin logs in and can see disabled records, Data Transfer, Audit and Recycle Bin.
2. PM can see both clusters and cannot mutate data.
3. PC Action Plans defaults to current month and only shows own hierarchy.
4. PC Export → Excel edit → Import → Preview → Confirm creates/updates that month's plans.
5. Prepare Next Month copies structure/Type/Notes and leaves Assigned Date blank.
6. DA sees only executable current-month plans for own villages.
7. DA Attendance designation with one master name selects directly; multiple names open the picker.
8. Early/Postponed requires Reason; On-time does not.
9. Report list stays concise; View shows member names, image, GPS and map.
10. Offline DA submission queues and replays once without duplicate server rows.
