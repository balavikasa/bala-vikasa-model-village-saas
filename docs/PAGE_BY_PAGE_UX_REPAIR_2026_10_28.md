# Bala Vikasa Model Village SaaS — Page-by-Page UX Repair

**Source baseline:** `balavikasa/bala-vikasa-model-village-saas`, `main` at commit `4a58f85aafdb5451ed7c47c2dbc22571301d53e0` (28 October 2026).
**Patch release:** `2026.27.26` (source-only; not production deployed).
**Operating model:** DA chooses an assigned village or **Other village**; the server records the attendance date; one village submission covers all committees, one shared photo/GPS fix and village-wide new-member count. PC Action Plans are no longer required to submit.

## Causes found in source and supplied screenshots

1. The legacy 12-column `.report-bento` grid gave some cards no defined column spans: the GPS/notes collapsed to one very narrow column in the village report.
2. Village profiles used **Plans / Draft / Assigned / On-plan pulse**, even though the new workflow is DA-led and no longer has scheduled committee assignments.
3. Analytics nested a complete Dash app in an iframe with large empty plots, duplicated headings and poor overflow behavior. An empty month looked like broken charts rather than a purposeful zero-data state.
4. Main navigation featured historical PC plans as if they were current DA work; DA mobile bottom nav led to Plans rather than villages.
5. Newly submitted village visits were called **On-time**, even though they have no assigned date. Report actions linked a planless visit to `edit=null` in the Master Data editor.
6. Report exports of new DA-led visits were aggregated and showed a numeric User ID in the DA column instead of the submitting DA's display name.

## Page-by-page inspection & modifications

| Page / component | Finding | This patch | Still requires staging/live QA |
|---|---|---|---|
| **Global desktop rail** (`base.html`) | Historical plan links in current nav; page/sidebar crowding | Primary nav focuses on Dashboard, Attendance (DA), Reports, Villages, Map, Monitoring, Analytics and Master Data. Preserves archive link in Dashboard/mobile non-DA menu. Shared min-width/overflow rules. | Check sidebar collapse and all roles at 760, 1024, 1440px |
| **DA bottom nav / mobile menu** | Plans was a primary action | Swapped DA Plans to Villages, added dashboard to mobile all-nav | Test iOS/Android PWA and menu keyboard handling |
| **Dashboard / Overview** | Current-month visits mixed with old Action Plan shortcut | Visit KPI wording; legacy plan link demoted to a text link for non-DAs; status bars sorted Done/Not done | Verify real data, scope and empty states |
| **DA Attendance Entry** | User-approved light teal theme | No destructive changes; retains one visit/all committees, GPS/photo/offline | Test with real committee member counts; ensure unassigned village path |
| **DA My Villages / village detail** | Draft, assigned dates, on-plan pulse | Backend derives committee last visit, current-month attendance and village visit state from actual attendance; template shows visited/pending and latest report | Verify role scoping, multiple-month history, empty villages |
| **Directory** | DA shown same all-role tabs | DA gets My Villages title and only Villages tab; others retain teams | Search and list card checks on mobile |
| **Village attendance report** | Narrow GPS/notes; huge evidence photo; dense members | Explicit summary/photo/table/GPS/notes grid; compact photo; collapsible member lists; accessible horizontal table overflow | Check large evidence photos, 8+ committees, no-photo handling |
| **Historical committee report** | Action Plan shown as current flow | Labels identify as historical/legacy; photo sizing bounded | Confirm older reports remain intact and read-only behavior is appropriate |
| **Reports list** | On-time status for no-plan submissions, invalid Edit link | New visits are `Recorded`; planless rows cannot create an invalid Edit plan link; total/recorded metrics | Check edit/delete/archive permissions, Excel download and filters |
| **Analytics** | Iframe with blank chart frames | Native responsive bar panels bound to `/api/v1/monitoring/series`, shows explicit no-data states | Verify real API data and role authorizations |
| **Monitoring** | Plan-centric wording/legend | Updated visit-focused headings and legend labels | Validate map pins with missing GPS and latest photo |
| **Map** | Risk/failure terminology from old workflow | Updated monthly-visit language | Review popup dimensions on phone |
| **Master Data** | Separate staff and login credentials; prior modal issues | No new business-logic changes (recent v2026.27.22/23 fixes preserved) | Verify create/edit, DA/PC password reset, account mapping |
| **PC/Admin data transfer** | Legacy imports still exposed | Left intact for master data and historical operations | Verify uploads on staging and permissions |
| **Action Plan management/transfer** | Old PC-based scheduler still accessible | Kept as historical functionality, not primary DA flow; no destructive removal | Decide whether to make fully read-only after stakeholder approval |
| **Legacy field page** (`field.html`) | Superseded by combined village attendance route | Kept for old links/data compatibility; no changes | Verify no active DA entry link points here |
| **Login** | Previously diagnosed linked User vs staff email mismatch | Preserved login/access patches; no new identity changes | Verify PC/DA credentials against live DB, with Admin approval |
| **Profile & offline utility pages** | Supporting pages | Profile state moved to visits; offline utility unchanged | Test offline queue and mobile sync after deploy |
| **403 / unauthorized** | Shared error view | No changes | Verify role boundaries remain enforced |

## Validation performed

- Python bytecode compilation of project modules and tests: **passed**.
- JavaScript syntax for modified scripts: **passed**.
- Jinja parse of all 19 templates: **passed**.
- Existing non-runtime static release validator: **passed** (its full runtime mode requires Flask dependencies unavailable here).
- 20 manually invoked static contract tests, including new visit-workflow UI tests: **passed**.
- Archive integrity and patch-application checks: see the accompanying packaging verification.
- **Not completed:** full pytest with Flask, PostgreSQL migration/integration tests, Ruff CI, a reliable headless browser screenshot, or actual production role/viewport walkthrough. This is **staging candidate**, not a production-verified release.

## Staging acceptance (recommended order)

1. **Database safety:** back up database and uploaded media; verify previous migrations already applied. This UI patch needs **no new schema migration**.
2. **Admin dashboard:** confirm `/healthz` returns release `2026.27.26`; compare village counts, visited and pending with October records.
3. **PC dashboard & scopes:** one PC sees only own village/DA scope and visit metrics; historical plan data accessible from archive only.
4. **DA account:** on phone, confirm dashboard > Attendance > My Villages > Reports > Map navigation and outside-assignment visit option.
5. **Village profile:** last visit, committee-level counts, and report links are correct; no Draft or assigned-date columns.
6. **Village attendance report:** GPS and remarks are readable cards; member list is expandable; photo does not take over the page; 390px and 1440px no horizontal body overflow.
7. **Reports list:** a new visit is `Recorded`, has no `Edit legacy plan` button, can be opened, and Excel export contains correct DA name.
8. **Analytics:** real data appears in the four panels; zero-data month shows usable empty states, not four empty Plotly axes.
9. **Map/monitoring:** field GPS appears if submitted and never masquerades as continuously tracked live GPS.
10. **Deployment verification:** run complete CI, including `python scripts/validate_release.py --require-runtime` and `ruff check .`; test a full field submission in staging, including offline synchronization, before promoting.

## Deployment notes

Apply the targeted Git patch to the exact GitHub baseline above, verify with `git apply --check`, commit and run CI. The updated source is also provided as a standalone ZIP. Existing migrations/records, account password hashes, and uploads are not modified by preparing this patch. This work was **not pushed to GitHub or deployed live**.
