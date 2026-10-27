# Bala Vikasa Model Village SaaS — v2026.27.20

## Change 1 — Action Plans: one assigned date per village

- PC/Admin can assign an Attendance date to one committee in a village in the Action Plans editor. The API automatically fills dates for the other **blank and editable** committee plans in the same village/month.
- Excel export format remains compatible (`Action Plans` sheet + hidden metadata). On import preview, any one dated committee row determines the date for blank rows belonging to that village, with `Attendance` inferred as the activity type. The preview explicitly displays inherited rows as new/changed. Only the confirmed import commits changes.
- Explicitly scheduled committee dates, locked historical records, archived records, and completed attendance are never overwritten. If a village's workbook contains conflicting explicit dates, the preview asks the PC to resolve blank rows rather than silently choosing one.
- Schedules continue to recur into later months through the previous release's recurring-plan logic, preserving manual/import overrides.

## Change 2 — Admin Master Data and staff login

- Fixed the `attendance-entries` Admin `ResourceSpec` argument error that could prevent the Master Data API from initializing properly.
- Login lookup now accepts common mobile number formatting variations (including Indian +91) while continuing to require the correct password, active account and role permissions.
- Added regression tests for Admin resource metadata and DA/PC login navigation. These are **not a substitute** for checking live database account status, password hashes, lockouts, migration state and production logs.

## Change 3 — DA one-village attendance

- Each committee is a compact accordion, with only one committee expanded at a time.
- Existing members appear in large color-coded, accessible, touch-friendly buttons grouped by President, Vice President, Secretary and Member. Gender is not displayed on the cards; selected names are visually highlighted.
- Male/female and total attendance are calculated automatically and verified again on the backend from the selected member IDs, using the existing database gender field. If selected members have no valid gender, the entry asks for Master Data correction instead of saving incorrect counts.
- One optional section for new-member counts appears at the bottom (still stored per committee), plus one shared early/postponed reason and one shared visit remark. A single photo, GPS fix and offline queue transaction continue to cover the whole village.
- Old queued offline payloads retain backward compatibility for their manually provided counts. No old Attendance or Specials history is deleted.

## Deployment — not performed by this package

1. Back up the PostgreSQL database and `UPLOAD_FOLDER` (the photo volume). The included sample workbook is not a substitute for production data.
2. Deploy the ZIP from a new Git branch to staging; run `python -m pip install -r requirements-dev.txt` and the full GitHub Actions sequence.
3. Run `flask --app wsgi db upgrade` if the previous 14-table attendance migration has not already been applied. No new migration is added in this release.
4. Check `/healthz`: release should be `2026.27.20`. Check `/readyz` returns 200 after PostgreSQL connects.
5. Login with separate Admin, PC and DA accounts. Confirm Admin `/api/v1/admin/resources` returns the resource list; staff login works with valid password; Admin resources are still denied to non-Admin users.
6. In the October Action Plan, assign **one** committee date in a village, save, refresh: every other blank editable committee plan in that village should have the same date. Export/import a workbook with only one dated row for a different test village and confirm inherited rows in the preview.
7. As a DA, open `/field/attendance?village=<assigned-village-id>`. Tap several names in different committees, verify automatic counts, new-member counts, single reason/photo/GPS and one submission; check online and offline sync. Photo paths must remain accessible through the persistent uploads volume.
8. Refresh the installed PWA or reopen after its updated service worker activates. Verify the new UI is visible before production cutover.

## Validation / limitations

- PASS: source Python compilation, JavaScript syntax checks, Jinja template static checks, existing release validation contracts and ZIP integrity.
- NOT VERIFIED here: Flask/SQLAlchemy integration tests, Ruff lint, Alembic migration smoke test against a running DB, visual browser screenshot and real login against the production database. The container cannot install missing Flask packages from its configured package index. GitHub and live deployment are not modified.
- An Admin 500 screenshot alone cannot prove the backend resource error is the only live cause. If `/api/v1/admin/resources` still returns 500 after deployment, inspect the application logs and database readiness; do not reset user passwords or alter production tables blindly.
