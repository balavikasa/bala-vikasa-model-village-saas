# Bala Vikasa Model Village - Reference Rebuild 2026.27.31

## What this release contains

This is an implementation of the six supplied reference compositions, not another generated mockup and not a screenshot used as a page background. Real HTML, Jinja templates, CSS, JavaScript and existing role-scoped data services power the controls and charts.

Rebuilt screens: Administration, Analytics, Dashboard, village profile, village attendance report, and mobile Attendance Entry. The shared navigation/header/theme also applies to secondary screens. Reference-derived decorative assets include the leaf-BV wordmark, sidebar village scene and header landscape. The former red logo is no longer displayed in the shared interface.

The application version is `2026.27.31`. This source is based on the supplied `2026.27.30` source archive, not an independently fetched latest GitHub commit.

## Preserved business rules

- DA login/home and `/overview` open Attendance Entry. `/dashboard` is an optional DA dashboard.
- DA selects an assigned village or uses Other village. Actual ownership and permissions are not transferred.
- The entry date remains server-controlled; the form does not submit an editable date.
- One village submission covers committee attendance, one village-wide new-member count, one photograph, one location and shared remarks.
- Existing password, CSRF, role permissions, historical reports and offline queue mechanisms remain in the app.
- No database model or migration is added by this release. Existing earlier migrations remain required when upgrading from older releases.

## Useful controls implemented

Administration: searchable live records; role and enabled-status filters; reset filters; preserved resource picker, editor, linked-account password form, recycle bin and audit history.

Analytics: period/cluster/DA/village/committee filters, five actual-data KPIs, coverage and gender rings, committee participation, monthly trend, DA comparison, map and data-derived insights. CSV export follows the displayed results and protects against spreadsheet formula injection. Failed requests clear stale results and disable stale exports.

Dashboard: scoped coverage, seven-day attendance trend, recent submissions, pending assigned villages, cross-assignment visit count and entry/report/village shortcuts. The seven-day window works across a month boundary.

Village profile: current attendance, available visit history, committee details, responsive table, recent visit timeline, filtered Reports and Map links, and authorized Edit/Attendance actions.

Village report: metadata strip, attendance totals, shared photograph, readable committee ledger, expandable additional member names, captured GPS, remarks and print/save-PDF. The production photograph comes from the existing authenticated photo endpoint, never the reference artwork.

Attendance: mobile-first three-section layout, initially collapsed committee cards, tap/undo selection, automatic totals, single-open accordion, shared new-member count, photo controls and GPS. Critical field controls retain at least 44px height on phones.

## Deliberate differences from the concept pictures

The references contain illustrative data and retired planning concepts. The implementation does not fabricate schedules, on-time percentages, growth comparisons, documents, household modules, user photographs, or production meeting photos. These are replaced with real current-workflow metrics and available routes. Account avatars use initials where no real avatar exists. New entries are Recorded, not On-time/Postponed.

The visual system follows the supplied imagery, but **a measured 99.9% pixel-match is not claimed**. Live data, text lengths, responsive sizes, browser fonts and map imagery will differ. The browser gallery shows exactly what was rendered in the local checks, not a second set of generated concepts.

## Verification actually completed

- 48 standalone source-contract/presentation tests, plus 6 unittest subtests: passed.
- 4 JavaScript unit tests: passed (safe labels, empty charts, count ticks, GPS validation).
- 15 Chromium interaction checks: passed with explicit sample API/storage/GPS fixtures.
- 30 responsive layout/navigation checks: passed across 320, 390, 768, 1280 and 1448px.
- 6 desktop composition gates: passed; no sidebar/content overlap or whole-page horizontal overflow in those cases.
- 23 production JavaScript files: syntax checks passed.
- 20 Jinja files, including the new component template: parsed successfully.
- Python compilation: passed.
- Screenshots: actual templates/styles/scripts rendered in Chromium, using labelled sample data.

The browser harness is isolated and is supplied separately. It does not connect to PostgreSQL, authenticate a Flask session, test real device permissions, or exercise the actual service-worker network lifecycle. No sample fixtures are installed in the production package. Obsolete standalone HTML previews were removed; the current browser evidence is packaged separately.

## Unverified gates - do not treat this as a production acceptance sign-off

Full `pytest` could not load because Flask and related dependencies are absent in the working environment. Attempts to install them were blocked by package-index DNS/network access. Ruff is also unavailable. Consequently, the full backend suite, migration smoke test, live authentication, PostgreSQL integration and real offline/device tests must run in CI/staging.

External fonts/map tile requests were blocked in the isolated browser. Captures use system-font fallbacks and the explicit map-tile error state; production maps still request OpenStreetMap tiles. No font files are distributed.

Author self-review was performed; no independent reviewer or subagent review was available. Critical review fixes include stale analytics results after errors, low-count chart tick labels, mobile touch heights, and filtering disabled-parent/other-submitter evidence in cross-assignment maps.

## Apply to the correct baseline

Back up the current repository, deployed database and uploads. The binary Git patch applies to the supplied v2026.27.30 baseline. It includes image assets, so use Git, not a text editor, to apply it.

```bash
git apply --check /path/to/Bala_Vikasa_v2026_27_31_Reference_Rebuild.patch
git apply /path/to/Bala_Vikasa_v2026_27_31_Reference_Rebuild.patch
python -m pip install -r requirements-dev.txt
python scripts/validate_release.py --require-runtime
ruff check .
node --test tests/js/reference-ui.test.cjs
python -m pytest -q
```

Do not force an incompatible patch. Reconcile local changes or use the full source archive in a separate staging checkout. Never replace production `.env`, database volumes or uploads with archive contents. The package has no live `.env`, database, account credentials or uploads.

Run the existing CI migration smoke test and stage against a backed-up PostgreSQL copy. Confirm `/healthz` reports `2026.27.31`. Test Admin, PC and DA with their actual permitted data. Confirm DA login opens Attendance, reset/edit controls work, totals match SQL, and an offline visit synchronizes once. Test camera/GPS on a physical phone and keep queued entries safe during service-worker activation.

The live website and repository were not changed by this work. There is no new schema migration solely for this UI rebuild.
