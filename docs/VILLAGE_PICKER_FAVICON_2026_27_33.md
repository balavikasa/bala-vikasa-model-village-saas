# Bala Vikasa Model Village - v2026.27.33

Baseline: the supplied v2026.27.32 Brand/Layout Fix application ZIP.

## Two requested changes

### DA Attendance: Other Villages inside the Village dropdown

The separate Other village button has been removed. The native Village dropdown shows the assigned villages first, followed by **Other Villages**. Selecting that item opens the searchable village list inside the same first-step card. The list is populated from the existing active-village API, excludes the already assigned villages, and searches by village name, mandal or district. All matching entries are reachable in a scrollable list; there is no 30-result truncation.

Choosing a result closes the search, shows that village in the dropdown, and loads its committees. Close or Escape restores the previous village without discarding member selections. Opening the search does not load an invalid village ID or permit submission before an actual village is chosen. The select now has a visible native dropdown arrow. Controls were checked at 320, 390, 768 and 1448 CSS pixels.

### Transparent browser favicon

The 16px, 32px and 64px PNG favicon files and the multi-size ICO now use a fully transparent canvas. They were regenerated from the existing transparent original Bala Vikasa emblem, preserving its red and grey details rather than erasing pixels from a white image. Sidebar/header/login branding and maskable PWA/Apple home-screen icons are unchanged; this request concerns the browser favicon.

The release and asset-cache identifiers are updated so the new favicon and scripts use fresh URLs. No IndexedDB database, queued attendance payload or browser site storage is deleted by this update.

## Scope and safeguards

- The approved theme, sidebar and report layouts are retained.
- Server-controlled attendance date, photo/GPS requirements, village-wide New members, roles, login, and submission API are unchanged.
- Cross-assignment submissions retain the existing `other_village` flag.
- No PostgreSQL schema migration is introduced.
- No live website, repository branch, password or production database has been changed.

## Executed validation

| Check | Result |
| --- | --- |
| New picker browser regression methods | 9 passed, including search, Close/Escape, counts, selection, full submission/reset and responsive touch controls |
| Transparent favicon tests | 2 passed with PNG and ICO checks at 16/32/64px |
| Existing browser interaction checks | 15 passed; the two old button interactions were adapted to the intentional new dropdown control |
| Previous v32 layout regression methods | 14 passed; the old button-overlap test now checks the search panel against the date fields |
| Existing responsive layout/navigation checks | 30 passed at 320, 390, 768, 1280, 1448px |
| Existing desktop layout checks | 6 passed |
| Standalone Python presentation/source tests | 8 passed |
| JavaScript unit tests | 4 passed |
| Static release checks | 25 passed, including Python compilation, 23 JS syntax checks and 19 top-level Jinja templates |

Browser tests render the actual application templates, styles and scripts using explicitly synthetic API/GPS responses. They are not authenticated production or PostgreSQL integration tests. The new picker tests and favicon tests were first run against the old behavior and failed; they passed after the changes.

Full `python -m pytest -q` was attempted and stopped during conftest import because Flask is unavailable. Installing requirements was attempted, but the environment's package index returned no Flask distribution. Ruff is also unavailable. Full CI, Flask/PostgreSQL, real-device GPS/camera and service-worker replay remain staging verification items, not passes. No independent reviewer was available; the changes received a local self-review.

## Installation

The full ZIP contains the cumulative application. The binary-safe Git patch applies to **v2026.27.32**, not to earlier releases.

From the repository root, with the patch stored outside the repository:

```bash
git apply --check /path/to/Bala_Vikasa_v2026_27_33_Village_Picker_Favicon.patch
git apply /path/to/Bala_Vikasa_v2026_27_33_Village_Picker_Favicon.patch
python scripts/validate_release.py --require-runtime
ruff check .
python -m pytest -q
```

Run CI and test on staging before production. Rebuild/redeploy to serve the changed templates and assets. `/healthz` should identify release `2026.27.33` after deployment.

Reload or reopen the browser tab for the favicon. Do not clear site storage to refresh icons: offline attendance may be waiting on the device. No extra database migration is needed when upgrading from v32.

## Browser QA reproduction

The separate QA ZIP includes the isolated fixture harness, new picker tests, adapted existing browser tests, screenshots, and execution logs. Point it at the extracted application:

```bash
export BV_APP_ROOT=/absolute/path/to/bala-vikasa-model-village-saas-main
export BV_QA_OUT=/absolute/path/to/qa-results
python harness/test_other_villages.py
python harness/test_interactions.py
python harness/test_v32_regressions.py
python harness/test_responsive.py 320 390 768 1280 1448
python harness/test_layout.py
python harness/capture_v33.py
```

Requires Playwright, Chromium, Jinja2, Pillow and PyMuPDF. The QA harness must not be installed as the production site.
