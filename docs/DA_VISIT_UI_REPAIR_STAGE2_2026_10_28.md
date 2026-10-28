# Bala Vikasa Model Village — UI Repair Stage 2 (v2026.27.27)

**Baseline:** v2026.27.26 page repair. This patch is incremental; apply v2026.27.26 first if the repository is still on an earlier release.

## Changes made

1. **Monthly Reports KPI cards** now show Total reports, Village visits recorded, People attended and New members. On-time/Postponed remain **legacy report filter values**, not the main DA-led performance metrics.
2. **Reports API summary** adds `people_attended` and `new_members` fields. For one village visit consisting of many committee rows, totals are aggregated *once per displayed visit*. Legacy committee records retain their existing status classification.
3. **Analytics no-data state** presents a clear explanation when every plotted value is zero, instead of four visually empty bar tracks.
4. **Monitoring GPS validation** rejects null, missing, empty, out-of-range and zero/zero coordinates. Previously, JavaScript `Number(null)` evaluated to zero, incorrectly making unmapped villages look geolocated.
5. **Unmapped village card** lists villages without valid GPS and provides links to their village profiles plus the full Map list view. It does not invent locations. When the Leaflet script is unavailable, the map shows a plain explanation rather than an empty, broken panel.
6. **Map List** supports `/map?mode=list`, shows a clear "GPS unavailable" label for unmapped villages, and retains all villages in the list rather than hiding them.
7. **Current map evidence** is attendance-only. Archived Specials remain in the database and historical reports, but are not used as latest live attendance photo/GPS.
8. **Release/cache identity** bumped to `2026.27.27` to ensure browsers load the updated JS/CSS.

## Role-by-role manual acceptance checklist

### Admin
- Confirm `/healthz` reports release `2026.27.27`.
- Reports (current month): compare people attended and new members with visible village report totals, not committee row count.
- Monitoring: missing GPS does *not* create markers near `(0,0)`; those villages appear in the new list below the map.
- Analytics: zero-activity categories display readable empty messages rather than 0% bars.
- Historical Extras/Specials reports still open and retain their old data.
- Master Data user/password actions remain as before (not modified by this patch).

### PC
- Confirm Reports, Monitoring and Map list are restricted to assigned DA/village scope.
- Confirm current-month visit totals match the village report and do not rely on old Action Plans.
- If the map has no valid locations, the village list remains usable.

### DA (mobile and desktop)
- Confirm approved light Attendance Entry theme is unchanged; one visit, all committees, one photo/GPS and village-wide new members.
- Visit My Villages, Reports, Map; confirm entries recorded outside own assignment remain accessible under Reports.
- `Map -> List` includes unmapped villages with GPS unavailable, and searching works.

### Viewports
- At 390px: check Report KPIs wrap in two columns; unmapped list links are touch-friendly; no body horizontal scrolling.
- At 768px: check sidebar and reports work without overlapping content.
- At 1366px: check map, KPI metrics and evidence report cards remain readable.
- On Android PWA: after deploy, close/reopen app and confirm new cache version loaded.

## Tests and deployment

Completed here:
- 20 JavaScript syntax checks; 19 Jinja parses; Python bytecode compilation.
- Non-runtime release contract checks.
- Node VM smoke test: unmapped GPS excluded and village names HTML-escaped; zero-data Analytics messages shown.
- Pure-function check: Report summary totals from multiple visits (legacy + DA-led) counted once per displayed row.
- Git patch applying to v2026.27.26 and ZIP integrity are checked during packaging.

**Not verified:** Flask and PostgreSQL integration, `pytest` under a full dependency environment, Ruff, browser screenshot visual QA, staging role tests or production deployment. The local Chromium browser stalled on page navigation, so no visual passing claim is made.

### Deployment

1. Back up production database and user-uploaded photos (routine safety); this patch does **not** introduce schema changes.
2. Apply the patch to the exact v2026.27.26 baseline. Do not overwrite a newer repository build blindly.
3. Run `python -m pip install -r requirements-dev.txt`, `python scripts/validate_release.py --require-runtime`, `ruff check .`, and `pytest -q` in CI.
4. Deploy to staging, verify all roles and viewports above, then release to production if approved.

This release deliberately **does not** alter DA entry validation, GPS permission requirements, password/account management, or historic attendance data.
