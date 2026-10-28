# DA Village Attendance — visual theme integration (v2026.27.24)

Design basis: the user-provided `Village Attendance-html.zip` artboard and mobile reference image. The artboard is used for colors, typography, spacing and layout; it is not bundled as a React runtime.

## Scope

Only the **DA /field/attendance** interface was redesigned. Admin, PC, PM, dashboards and their existing theme are unchanged. No database migration or change to the attendance API was introduced.

- Single column of three rounded cards with the supplied light aqua/white appearance
- Village/date selectors and three summary pills
- Expandable, compact committee cards; only one open at a time
- Member name tiles ordered by role (President, Vice President, Secretary, Members), and selected via `aria-pressed` buttons
- Auto-calculated male/female/total counters, using the existing member gender metadata; gender is **not displayed** on the tiles
- Shared date-change reason shown only when required, optional per-committee new-member counts, single notes field
- Shared photo via camera / gallery / files and current device GPS; existing auto-location consent rules remain
- Existing offline queue and secure one-village submission still use `/api/v1/attendance/village`

## Changed files

`app/templates/village_attendance.html`, `app/static/js/village-attendance.js`, `app/static/css/attendance-theme.css`, `app/static/sw.js`, `app/__init__.py`, `pyproject.toml`, `tests/test_release_identity.py` and new `tests/test_attendance_theme.py`.

## QA

Static release checks and Chromium visual/interaction QA were run using mocked API responses (no changes to live data). Selected one male and one female member: totals became **Male 1, Female 1, Total 2**; progress became **1 of 7**; Next committee opened Farmer. These tests validate UI behavior with mock records, not production end-to-end submission.

CI must run `python scripts/validate_release.py --require-runtime` and `ruff check .` before staging deployment. Check `/healthz` for release `2026.27.24`. Reload the installed PWA to pick up the new service worker and CSS. Verify real role scoping, current-month plan eligibility, GPS/photo permission, offline queue, synchronization, and report entry on staging.

### Important

The included complete ZIP also retains the prior login-recovery script/runbook from the earlier provided recovery bundle. The **targeted Git patch intentionally excludes those files**, since they already exist on the current repository branch.
