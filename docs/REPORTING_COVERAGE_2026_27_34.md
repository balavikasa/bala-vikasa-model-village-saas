# Bala Vikasa Model Village - Reporting & Village Coverage v2026.27.34

## Delivery scope

This release implements the approved v33 coverage/reporting audit. It adds an operational reporting register and a shared reporting-period contract. It does not replace the approved visual theme or change how DAs submit attendance.

Baseline: `Bala_Vikasa_Model_Village_v2026_27_33_Village_Picker_Favicon.zip`.
Target release: `2026.27.34`.
No production website, database, account, or GitHub branch has been modified. No schema migration is added by this release. Existing migration requirements for earlier releases still apply.

## Where to use it

- Admin / PM / PC desktop: **Coverage** in the sidebar.
- DA/mobile: **More -> Coverage**. DA still opens directly into Attendance Entry.
- Dashboard, Monitoring, Analytics, Maps, Reports and profile drill-downs have reporting-period controls or period-preserving links into Coverage.
- Direct route: `/coverage` (authenticated).

### A complete Done/Pending workflow

1. Select the reporting period and apply it.
2. Set Cluster, PC, Assigned DA, Submitted by DA, Village or Committee as needed. Access is always restricted by the existing server-side role rules.
3. Select **All villages**, **Done** or **Pending**, or click the matching KPI card.
4. Search by village, mandal, district or assigned team. Browse all results with pagination (10, 25, 50 or 100 per page).
5. Read visit/last-visit dates, assigned DA/PC, actual submitting DA, male/female/attendance totals, new members and report links.
6. **Export selection** downloads XLSX for all matching rows across all pages. CSV exports the same village selection.

The top cards describe the selected period and village filters, independent of the active status tab. The register shows a separate **This selection** summary for its current status. For example, Pending can show 41 villages and zero recorded attendance while the top cards show 2 Done and 34 attendances elsewhere in the same scope. This distinction is explicitly labelled.

## Supported reporting periods

Today; Yesterday; Select day; This week; Last week; Select week; This month; Last month; Select month; This year; Last year; Select year; Custom From/To; All time.

Weeks are Monday-Sunday. Boundaries use the application's Asia/Kolkata-local entry dates, not the browser clock. Custom endpoints are inclusive. Existing `month=YYYY-MM` links continue to work. Invalid/reversed dates return validation errors instead of silently falling back to an unrelated period.

Only the reporting-period choice is saved in browser session storage. Opening another reporting page keeps that choice unless its URL explicitly selects a period. No account credentials or report data are stored by this selector.

## Counting rules

### Village coverage

- The denominator is the current active village population within the viewer's authorized scope and chosen village filters.
- **Done** is distinct villages with a qualifying, active village-attendance submission and active committee entries within the selected dates.
- **Pending** is the complement of Done in exactly that denominator.
- `Total villages = Done + Pending`.
- Pending means **not visited in the selected period**, not overdue. No daily obligations or PC schedules are invented.
- A separate current-month context line distinguishes monthly Pending from a selected day/week's non-visited population.
- For multi-month ranges, the main number is distinct villages across the range. The month-by-month section evaluates each month's intersection with the selected dates; a visit in one month does not complete another month.
- Historical assignment snapshots do not exist in this schema. Historical ranges deliberately use **current active assignments**, clearly labelled.

### Attendance and new members

- Male/Female/Total are sums of active committee attendance instances, not guaranteed distinct individuals across committees or dates.
- **New members** is the separate village-wide value, counted once per village submission. It is not added to registered-member attendance or repeated for each member name/committee export row.
- Pending rows have blank attendance values instead of fabricated zeros indicating a visit.
- The current server-assigned entry date remains uneditable. Offline attendance retains the existing acceptance-date rules; this release does not change them.

### Assignment versus work performed

- **Assigned DA** filters village responsibility.
- **Submitted by DA** filters actual work. When selected, Done explicitly means recorded by that DA within the viewer's authorized village population.
- Team rows show assigned/done/pending responsibility separately from the DA's actual submissions, attendance, new members and visits outside their assignment.
- Active DAs with zero submissions remain visible.
- A DA's own **Other villages** view does not expand their assigned denominator. Managerial cross-assignment work appears in the team matrix. Existing permission rules remain unchanged, including cross-PC visibility restrictions.

### History and inactive data

- Disabled/deleted villages, visits and child entries do not inflate current operational coverage.
- Standalone legacy committee attendance remains accessible in Reports. It is not silently promoted to a completed all-committee village submission.
- Coverage shows an explicit historical-record count/notice. Historical Reports and complete-village Coverage answer different, labelled questions.
- Recent-activity previews may remain short. Their display limits no longer determine Done/Pending populations.

## Export behaviour

XLSX includes Summary, Villages, matching Done/Pending sheets, Submissions, Team - scope and Monthly coverage - scope. Done/Pending sheets contain only the selected status/search population. Team and monthly sheets are explicitly scope summaries, not pretend status-filtered lists. CSV contains the complete selected village rows.

Pagination changes only the displayed page. It never truncates the export. Search and all applied filters are included in the export query. Export links are disabled immediately when filters/search change, remain disabled on errors and become available only for the latest successful response. Spreadsheet cells derived from user text are protected against formula injection.

The existing Reports ledger now displays Male, Female, Total and New Members. Its server-side search, totals and Excel export use the same matched report rows. Mixed historical plan-linked and planless children under one village visit are exported once, without losing linked children or multiplying village-wide totals.

## Audit mapping

| Finding | Source correction |
|---|---|
| G01 Complete Pending list | Complete register, pagination, search and matching export; no 5/3-item ceiling. |
| G02 Complete Done list | Distinct-village register paired with Pending; click-through KPI cards. |
| G03 Daily reporting | Today/yesterday/day plus the same details, totals and export. |
| G04 Weekly reporting | Calendar weeks, including month/year crossover. |
| G05 Monthly consistency | Shared period engine and browser period controls across reporting pages. |
| G06 Range/year/all time | Common inclusive range resolver and monthly coverage breakdown. |
| G07 KPI drill-down | Coverage links/status tabs behind operational KPI cards. |
| G08 Team matrix | Owner vs submitter metrics and zero-submission staff included. |
| G09 Report-row totals | Male/female/total/new columns added to existing Reports. |
| G10 Full status export | All matching villages, including Pending, exported across pages. |
| G11 Search/summary/export | Server-side report search; stale exports invalidated immediately. |
| G12 Period-correct maps | Same period and population as charts; historic last-visit dates do not override Pending status. |
| G13 PM operational profile | Selected-period visit/coverage/attendance/new-member metrics replace operational plan emphasis. |
| G14 Active denominators | Shared active-record policy without changing Admin maintenance permissions. |
| G15 Legacy interpretation | Complete-parent coverage explicit; standalone history retained in Reports. |
| G16 Owner/submitter ambiguity | Distinct filters, column labels and Other-work accounting. |
| G17 Recent-query cutoff | Coverage computed from complete scoped population, not a 120-row feed. |

These mappings describe implemented source paths, not a claim that all production acceptance cases have been exercised.

## Offline/report freshness

Reporting APIs now require a network response. The service worker must not show cached prior-day data as a successful Today report. Offline reporting shows an explicit connection-unavailable result. Field reference caching and the attendance submission/outbox queue are unchanged. Do not clear site storage to update the release; it may contain queued attendance.

## Verification performed in this environment

| Check | Observed result |
|---|---|
| Framework-independent period/coverage tests | 19 tests passed, with boundary/selection subcases. |
| Workbook/CSV tests | 3 tests passed. |
| JavaScript unit tests | 29 tests passed. |
| Actual SQLAlchemy models, scope queries and services against SQLite | 17 main assertions passed; framework-extension bridge is test-only. |
| Mixed plan-linked/planless visit export | Report and workbook totals 29; new members 29 once, passed. |
| Larger dataset / legacy / disabled records | Five additional checks passed; 193 active / 152 Done / 41 Pending fixture. |
| Profile totals/filter consistency | Selected-day and submitter-filtered committee checks passed. |
| Profile malformed-date errors | Four isolated handler-body checks passed; JSON error path, not HTML-string output. |
| In-memory Chromium | 21 checks passed, including actual shipped templates/CSS/JS and SQLite-service fixture transport. |
| Responsive register | Checked 320, 390, 768, 1280 and 1448px for body overflow. |
| Existing no-framework source checks | 40 functions passed; these are not the full pytest suite. |
| Static release validation | Python compilation, 25 JavaScript files and 20 Jinja templates passed; bundled workbook contracts passed. |
| Full pytest | Blocked during conftest import: Flask is not installed. |
| Ruff | Blocked: Ruff is not installed. |
| Full Flask routing/login/CSRF and PostgreSQL | Not executed here. Seven additional Flask acceptance tests are included for normal CI. |
| Production website | Not changed or authenticated/tested by this release task. |

Chromium screenshots use synthetic test data and fallback fonts. They render the actual application templates and JavaScript in memory. A local-server navigation attempt was blocked by browser policy; it was not bypassed. In-memory rendering uses an explicit test transport rather than a logged-in Flask server. It cannot establish production authentication, cookies or PostgreSQL correctness.

## Review and remaining risks

Final review was a self-review by the implementation author; no independent reviewer was available. Scope/exports, mixed historical rows, request races, stale reporting cache, map status and structured error paths were inspected and corrected with focused checks. Actual Flask authentication and production database behaviours still require CI/staging.

The shared adapter reads complete authorized history to make last-visit metadata and all-time reporting correct. Query-level aggregation/pagination optimization for very large datasets is deferred; correctness must never reintroduce a recent-feed cutoff. Historical assignment reconstruction is not added. The existing Reports download filename retains its original monthly naming format; the workbook's Selection sheet identifies the actual full selected period.

## Deployment

1. Back up PostgreSQL and uploaded evidence using your normal process.
2. Use the full source ZIP, or apply the targeted patch only to an unchanged v2026.27.33 baseline. Reconcile newer repository edits before applying; never force it onto a different tree.
3. Run normal CI: `python scripts/validate_release.py --require-runtime`, `python -m pytest -q`, `ruff check .`, `node --test tests/js/*.cjs tests/js/*.js`, and the existing migration smoke test.
4. Deploy to staging. Check `/healthz` returns `2026.27.34`.
5. Verify Admin, PC and DA Coverage, selected dates, Done/Pending, Other-work attribution, exports, disabled/legacy records, and mobile navigation with real authorized accounts.
6. Verify DA still opens Attendance, Other Villages search still works, and queued offline attendance is intact.
7. Deploy to production only after staging acceptance. There is no additional migration in this release.

No deployment, password reset, production data write, deletion, or repository push was performed in this task.
