# Bala Vikasa Model Village - v2026.27.32

## Scope

Targeted corrections against the supplied v2026.27.31 Reference Rebuild. This is not a new theme or workflow redesign. There are no schema migrations, production account changes, or attendance-data changes in this update.

## Branding

The original user-supplied red and grey Bala Vikasa emblem replaces the generated teal monogram. A shared HTML brand component pairs that emblem with live, sharp text: **Bala Vikasa / Model Village**. The year is removed from visible branding, not from actual report dates or historical records. The desktop brand has the previous 204 x 52 CSS-pixel footprint; the mobile version scales down. Sidebar, mobile header, login, favicon, Apple touch icon and PWA icons use the original emblem. Favicon URLs and application assets carry the new release version.

## Verified causes and corrections

| Area | Cause found | Correction |
| --- | --- | --- |
| Main content / sidebar | The fixed-position shell produced different paint origins in full-page Chromium captures; medium layouts had conflicting grid rules. | Real desktop grid tracks with sticky navigation and header; a two-column dashboard at intermediate widths; readable, full-width quick actions. |
| Recycle Bin | The legacy horizontal flex card put long labels and both buttons in a narrow three-column card. | Vertical cards, wrapping content, readable expiry dates and a bottom action row; actions stay inside each card at all tested widths. Restore/delete API operations and confirmations are unchanged. |
| Map List | The list reused a phone-only class that was hidden on desktop. | Dedicated responsive list grid, result count and visible loading/error/retry states. |
| Map tiles | The application rendered tile.openstreetmap.org, but CSP allowed only its wildcard subdomains. The custom map renderer suppressed the referrer. | Allow the precise tile host and send strict-origin-when-cross-origin. No broad wildcard or script-policy relaxation. Existing missing-tile fallback remains. |
| DA entry initial state | Progress was displayed before a village was chosen, with no initial zero width. | Hide progress until a village with pending committees is loaded; preserve all actual attendance counts. Keep the Other village control clear of the date fields. |
| Report printing | The skip link leaked into print; collapsed disclosure sections omitted names; screen cards fragmented across pages. | Print-specific report layout, complete print-only member roster, eager evidence photograph, compact metadata, and a grouped footer. The printed map area becomes captured coordinates plus a clickable location link rather than an unavailable tile widget. |

OpenStreetMap policy reference: https://operations.osmfoundation.org/policies/tiles/
CSP reference: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy

The supplied Ganeshpalli PDF had three pages, including an isolated metadata page and visible "Skip to content" links. A synthetic 24-attendee/eight-committee report using the corrected application prints in two pages and includes every selected member. This is a test fixture, not a regenerated production report. Longer names, additional members, paper size and browser print settings can change pagination.

## Preserved behavior

- DA login and application home remain Attendance Entry first.
- Assigned villages and Other village selection remain available.
- The server-controlled entry date, village-wide new-members field, committee member selection, shared photo, GPS and one village submission are unchanged.
- Existing role scope, authentication, password reset, reports, audit records and database migrations remain intact.
- Offline queue storage and pending submissions are not cleared.
- Existing light/teal/ivory theme, village illustrations and page structure are retained.

## Verification performed

All checks below ran on the packaged source before delivery:

| Verification | Result |
| --- | --- |
| Targeted Chromium regression methods | 14 passed, including desktop map list, error visibility, original emblem/favicon, recycle buttons, medium dashboard, print roster and full-page shell stability. |
| Existing browser interactions | 15 passed: administration controls, attendance selection/counting/payload, evidence requirement, analytics and report disclosure. |
| Responsive geometry / navigation | 30 passed: six pages at 320, 390, 768, 1134 and 1448 CSS pixels. |
| Desktop reference layout checks | 6 passed. |
| Dependency-free Python source/calculation tests | 47 passed, plus 6 subtests. These are not the complete application test suite. |
| JavaScript unit tests | 4 passed. |
| Syntax/static release validator | Python compilation, JavaScript syntax, template parsing and existing static contracts passed. |
| Archive, source hashes and patch | Verified after final packaging. |

Browser tests use the real templates, CSS and scripts with synthetic API/storage/GPS responses. They do not log in to production. External requests are intentionally blocked in ordinary captures, so maps show the fallback state and external fonts use fallbacks. A separate browser CSP test successfully loads a synthetic image from the exact allowed map host; this proves policy acceptance, not public tile-service availability.

### Checks that could not be completed

The complete `python -m pytest -q` command was attempted and failed at collection because Flask is absent. The required Flask extensions are also missing. Installing requirements was attempted, but the package index could not be resolved from this environment. `python -m ruff check .` was also attempted; Ruff is not installed. Live PostgreSQL, signed-in role testing, real camera/GPS permissions and actual offline service-worker replay remain unverified. Full CI and staging acceptance are required.

### Review

A separate author self-review checked the diff for accidental workflow changes, broad CSP relaxation, unsafe interpolation, data changes and broken script hooks. No independent reviewer was available. Existing database models, services and migration files are unchanged. No passwords or production database credentials were used.

## Apply to the repository

Choose one method, not both:

1. For the existing **v2026.27.31** codebase, apply the supplied binary-capable Git patch on a new branch:

```bash
git switch -c fix/v32-brand-layout
git apply --check /path/to/Bala_Vikasa_v2026_27_32_Brand_Layout_Fix.patch
git apply /path/to/Bala_Vikasa_v2026_27_32_Brand_Layout_Fix.patch
python -m pip install -r requirements-dev.txt
python scripts/validate_release.py --require-runtime
python -m ruff check .
python -m pytest -q
```

2. Alternatively, extract the full application ZIP into a clean source directory and compare it with your current repository. Keep production environment variables, upload storage and the database outside replacement operations. Never replace production wholesale over a directory containing unsaved changes.

Stop if the patch check fails; do not force it onto another revision. The existing project CI includes its migration smoke test and should pass before deployment. No new migration was added by v32; previously required v25 migrations still apply to older installations.

## Staging acceptance

Confirm `/healthz` reports release `2026.27.32`. Rebuild/redeploy the app so the new templates and asset cache version are served. Reload the browser; the versioned favicon may still require closing and reopening the tab. Installed PWA icon refresh timing is controlled by the browser/platform.

Do not clear website data or IndexedDB merely to refresh the icon; pending offline attendance may be stored there. Synchronize or safely preserve pending submissions first.

Check these cases with real Admin, PC and DA accounts:

- Original emblem and year-free brand on login, desktop sidebar, phone header and browser tab.
- Dashboard at laptop width, regular scrolling, and a full-page capture: no main content behind the sidebar/header.
- Recycle Bin with long names: both actions visible; test restore/delete only on disposable staging records.
- Map List at desktop and phone widths: records, filtering, empty state and service-error message visible. Verify map tiles over the deployed HTTPS origin.
- DA home opens Attendance, blank selection has no fake progress, Other village/date controls do not collide, selected member counts still update.
- Print an actual report before expanding any member disclosures. Every selected member should appear, navigation should be absent, and location/remarks/metadata should remain readable.

The live website has not been changed by this delivery.
