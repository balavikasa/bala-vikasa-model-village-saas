# Bala Vikasa Model Village SaaS — 2026–27

Release **2026.27.9** is the mobile-first SaaS rebuild for the Sopar-funded Bala Vikasa Model Village
Program. It uses the approved project documentation and dashboard prototype as the product baseline,
while preserving the normalized master data and Flask/PostgreSQL architecture.

## Product baseline

Program scope:

- 2 PMs
- 2 PCs
- 9 DAs
- 42 villages
- 351 committees
- 2,433 committee members
- CSRB and PDTC clusters

`PC.cluster` is the only persisted cluster source. DA and Village inherit Cluster through relationships.

Role behavior:

| Role | Primary job |
|---|---|
| Admin | Global administration, users, master data, audit, recycle bin, imports |
| PM | Global read-only monitoring |
| PC | Own-team monitoring and monthly Action Plan management |
| DA | Own-village field execution: Attendance and Specials |

## What changed in the SaaS rebuild

### Mobile-first Bento UI

The application now uses a restrained Bento Grid + Minimalism interface with role-specific phone
navigation:

- DA: Entry · Plans · Reports · Map · More
- PC: Home · Plans · Team · Reports · Map
- PM: Home · People · Plans · Reports · Map
- Admin: Home · Plans · Reports · Map · Admin

Tablet/desktop use a side rail, wider tables and analytics panels. The PWA manifest, service worker,
offline shell and IndexedDB submission outbox remain part of the application.

### Monthly PC Action Plans

Action Plans are monthly occurrences. The page opens on the configured program's current month and
shows the current date/time.

PC can:

- edit a single monthly plan in the portal;
- Export a month to Excel;
- edit Type / Assigned Date / Notes;
- upload and Validate;
- review New / Changed / Unchanged / Error rows;
- Confirm atomically;
- Prepare Next Month by copying Type/Notes and structure, **not dates**.

Past/completed/overdue schedule history is immutable to PC edits. Each committee has at most one plan
occurrence per month.

Existing pre-rebuild ActionPlan rows remain as non-executable legacy/template rows with
`plan_month=NULL`; they are preserved during migration.

### DA Attendance

DA selects Village → Committee → assigned current-month Attendance plan.

Status is server-derived:

- before assigned date → **Early**, Reason required
- same date → **On-time**, Reason hidden/not required
- after assigned date → **Postponed**, Reason required
- passed date with no submission → **Failure** in monitoring/reports

Attendance includes live Male/Female counts, server-computed Total, master totals, New Members Count,
Visit Designations, Committee Member Name selection, WebP evidence photo, GPS and remarks.

For Visit Designations:

- 0 master names → designation unavailable
- 1 master name → tapping selects that person directly
- 2+ master names → searchable multi-select picker

Selected people are stored by master ID plus name/designation/gender snapshots for immutable history.

### DA Specials

Specials uses an assigned current-month Specials plan. Current Special name follows Committee until
the real Specials catalogue is supplied. Scope is exactly **Under GP** or **Under VDC**.

### Reports

The report ledger is intentionally simple:

`Date · DA · Village · Committee · Type · Status · View`

`View` opens the complete detail screen with counts/participants, selected Committee Member Names,
reason, evidence image, GPS and map. Excel export includes Committee Member Name + Visit Designation.

### Maps and directory

The Village Map is role-scoped and has Map/List modes for phone use. PM/PC/DA/Village directory
profiles provide drill-downs without exposing out-of-scope records.

### Admin master-data transfer

Admin has a reusable **Export → Edit → Validate/Preview → Confirm** workflow for:

- PMs
- PCs
- DAs
- Villages
- Committees
- Committee Members

Omission never deletes a row. Relationship changes are shown as **Moved** and audit-logged.
User/password bulk import is deliberately excluded. Monthly Action Plans use their dedicated planning
transfer workflow.

## Repository map

```text
app/
  __init__.py
  models.py
  scoping.py
  auth.py
  api.py
  planning.py
  reports.py
  admin_api.py
  admin_transfer.py
  dashboards.py
  pages.py
  timeutils.py
  services/
    entries.py
    files.py
    monitoring.py
    monthly_plans.py
    reports.py
    profiles.py
    master_transfer.py
    workbook.py
  templates/
  static/
    css/app.css
    js/
    manifest.json
    sw.js
migrations/versions/
  20260821_0001_initial_schema.py
  20260822_0002_monthly_planning_reports.py
tests/
docs/
  PRODUCT_BASELINE_2026-08-22.md
  DATA_MODEL.md
  RBAC.md
  API.md
  ACCEPTANCE_CRITERIA.md
  UPGRADE_2026.27.3.md
  reference/
```

## Local development

Python 3.11+:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m flask --app wsgi db upgrade
python .\scripts\bootstrap_admin.py
python -m flask --app wsgi run --debug
```

Open `http://127.0.0.1:5000`.

## Upgrade an existing local database

**Back up first.** Do not test a schema migration against your only database copy.

```powershell
Copy-Item .\instance\model_village.db .\instance\model_village.before-2026.27.3.db
python -m flask --app wsgi db upgrade
```

The migration preserves the existing 351 legacy ActionPlan rows. New monthly Action Plans are then
created through the PC planning page.

See `docs/UPGRADE_2026.27.3.md` for the recommended new-folder migration procedure.

## First PC monthly planning workflow

1. Sign in as PC.
2. Open **Action Plans**.
3. Confirm the current month at the top.
4. Open **Export / Import**.
5. Export the selected month.
6. Fill/adjust Type, Assigned Date and Notes in Excel.
7. Import the same workbook for the same month.
8. Review the preview.
9. Confirm.
10. Sign in as DA; assigned plans now appear in Attendance/Specials.

At month-end, use **Prepare next month**, then export that new month and set fresh dates.

## Existing master data

The rebuild does not require re-importing the master workbook when upgrading an already-populated
database. Expected master counts remain:

| Entity | Count |
|---|---:|
| PMs | 2 |
| PCs | 2 |
| DAs | 9 |
| Villages | 42 |
| Committees | 351 |
| Committee Members | 2,433 |
| Legacy ActionPlan templates | 351 |

For a completely empty environment, use the approved normalized seed/import process before monthly
planning.

## Database schema

There are 13 physical tables after migration:

`pms`, `pcs`, `das`, `villages`, `committees`, `committee_members`, `action_plans`,
`attendance_entries`, `attendance_visit_members`, `specials_entries`, `users`, `audit_logs`,
`recycle_bin`.

## Verification

Run locally after installing dependencies:

```powershell
python -m compileall -q app migrations tests
python -m pytest
python -m ruff check .
```

If Node is installed:

```powershell
Get-ChildItem .\app\static\js\*.js | ForEach-Object { node --check $_.FullName }
node --check .\app\static\sw.js
```

Then exercise the role acceptance criteria in `docs/ACCEPTANCE_CRITERIA.md`.

## Production notes

- PostgreSQL is the production database; SQLite is for local development.
- Set a strong `SECRET_KEY`.
- Set `SESSION_COOKIE_SECURE=1` behind HTTPS.
- Keep `APP_TIMEZONE=Asia/Kolkata` unless the program timezone changes.
- Evidence uploads need durable/shared storage before horizontal web scaling.
- Back up the database and evidence files as one recovery set.
- Rate-limit authentication at the ingress/application boundary.
- Run recycle-bin purge only after backup health is verified.
- Do not use the included local test credentials in production.

Hotfix 2026.27.4 also adds Windows timezone portability and corrected normalized-workbook ID header discovery.

The authoritative rebuild decisions are recorded in `docs/PRODUCT_BASELINE_2026-08-22.md`.


## Final release notes — 2026.27.9

This package consolidates the tested rebuild and UI hotfixes through the final UAT cycle:

- role-aware desktop/mobile navigation and visible sign-out controls;
- DA landing on `/field/attendance`;
- mobile UI density/typography polish;
- stable `basic` Flask-Login session protection for browser/PWA use;
- Admin report Edit/Delete/Recycle Bin controls with soft-delete/restore;
- responsive Leaflet report maps;
- Admin Recycle Bin navigation from the shared shell;
- removal of the duplicate DA Online/Offline card (the top bar remains authoritative);
- Windows-safe navigation glyph encoding;
- monthly Action Plan Excel export/validate/preview/confirm workflow;
- regression tests covering session stability, shared-shell encoding, report controls, maps and mobile UI.

The distributable deliberately excludes real `.env` secrets and production/local database contents.
Keep the existing `instance/model_village.db` when upgrading an accepted local installation, then run
`python -m flask --app wsgi db upgrade`.

The final UAT report is included under `docs/qa/`.


## Hostinger VPS + Coolify production deployment

Use the dedicated production guide:

`docs/COOLIFY_HOSTINGER_DEPLOYMENT.md`

For Coolify, deploy this repository as a **Dockerfile Application** on internal port `8000`, use a
standalone **Coolify PostgreSQL** resource on the same destination, and mount a named persistent volume at
`/srv/app/uploads`.

`docker-compose.local.yml` is intentionally local-only and should not be selected as the production
Coolify deployment source.


**Production database:** PostgreSQL is the supported production database for this release; SQLite remains for local/tests only.
