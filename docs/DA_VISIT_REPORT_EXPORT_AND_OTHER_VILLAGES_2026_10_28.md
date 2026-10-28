# Model Village v2026.27.28 — DA visit reports and cross-assignment QA

**Release stage:** staging candidate. Built on v2026.27.27 (Monitoring & Reports QA). No new database migration.

## Issues verified in v2026.27.27

1. The DA-led Excel report exported a *single village summary row* with no individual committee names, no selected committee member names, and no visit designations. This contradicted the village report page and made source verification difficult.
2. When a DA used **Other village**, the dashboard could increase the total village scope. This incorrectly changed the denominator for the DA's assigned-village completion KPI.
3. The DA map showed only villages formally assigned to that DA, so the DA could not see the evidence location of a visit they submitted through **Other village**.
4. Admin's default read-scope includes disabled records for recovery. Current visit KPI and reports needed explicit active-visit filtering to avoid counting recovered/deleted/disabled records as current completions.

## Changes in this release

- **Report Excel**: every active committee in a DA-led village visit has rows with selected member names and their designation snapshots. A committee with no selected members still appears as a row. Male/Female/Total are written once per committee, not repeated on every selected-member row. The *single village-wide* New members value and evidence URL are written once per village visit. Original 23-column export remains intact, and historic Action Plan reports remain available. Historic multi-member attendance counts are also no longer duplicated on repeated member-name rows.
- **DA Dashboard**: Villages / Villages done / Villages not done keep the assigned-village denominator. An independent **Other villages visited** KPI counts distinct outside-assignment villages submitted by that DA this month. People attended / New members still include the DA's own cross-assignment submissions.
- **DA Map**: includes the DA's assigned villages and any other active village for which that DA has a valid submitted village attendance visit. Such a location is labeled **Other village · visited by you**; ownership and master assignment are not modified. Admin/PC/PM map visibility is unchanged.
- **Current monitoring/report filters**: disabled/deleted parent village visits do not contribute to current month totals, charts, report ledgers, or Excel exports. Admin can still manage those via Master Data/recovery tools.
- **PWA** cache identifier and application health version changed to `2026.27.28`.

## CI and staging acceptance

1. Apply the patch **only after v2026.27.27** and run `python -m pip install -r requirements-dev.txt` in GitHub CI.
2. Run `python scripts/validate_release.py --require-runtime`, `ruff check .`, and `pytest -q`; the newly added tests for Excel and Other-village logic should pass.
3. Sign in as DA. Submit a current-month visit for an *assigned village*. Confirm dashboard done count increments once; reports show one village submission; Excel contains one row per selected member and committee (no duplicate totals).
4. Test a DA's **Other village** visit to a village belonging to another DA. Confirm assigned-village total is unchanged; **Other villages visited** increments by 1; report is visible to the submitting DA, and the visited village appears on their map with the Other label.
5. On Admin and the owning PC account, verify the visit is counted in the village's own cluster/scope without changing its DA assignment. Check that an unrelated PC does not gain access outside their existing scope.
6. Mark a test village visit disabled/archived in staging. Confirm that current KPIs and Excel no longer count it; restore it and confirm figures return as expected.
7. Check report Excel filters by month and type; check a committee with **zero attendance** is retained in export. Test desktop and mobile map/List toggles and card sizing.
8. Do a full PostgreSQL backup and field-photo backup before production rollout.

## Validation performed here

- PASS: Python bytecode compilation, JavaScript syntax, Jinja template parsing, static release contracts.
- PASS: dependency-free isolated member-export smoke tests, including zero-attendance committee and nonduplicated aggregates.
- NOT RUN: full Flask/SQLAlchemy/PostgreSQL integration tests or Ruff. The container lacks Flask packages and package installation failed. Added pytest regressions for CI.
- NOT RUN: production login, real GPS/photo submission, and cross-role browser visual QA. The live website is unchanged.

**Deployment:** Apply in staging first. `/healthz` should return `release: 2026.27.28`. No schema migration is included; the prior DA-led migration must already be applied.
