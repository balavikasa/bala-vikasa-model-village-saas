# Release 2026.27.25 — staging acceptance

1. Back up the live PostgreSQL database **and photo uploads** before updating any container.
2. Deploy the changed source on staging and run `python -m flask --app wsgi db upgrade`. Confirm `alembic_version` is `20261028_0004`.
3. Run `python scripts/validate_release.py --require-runtime` and `ruff check .` on CI. The added pytest cases cover the revised behavior; these have not run in this artifact environment.
4. With a DA account, open the dashboard and verify **Villages done**, **Villages not done**, **People attended** and **New members** for the current month.
5. In Attendance, verify the assigned-village dropdown contains only owned villages. Choose **Other village** to search and select an unassigned active village.
6. Confirm the date is displayed but cannot be edited, and the server date is recorded regardless of browser manipulation. Check server timezone is Asia/Kolkata.
7. Select members in every committee, enter one village-wide New members number, and upload one photo with valid GPS. Submit without any pre-existing Action Plan. Verify the village report and counts.
8. Reopen the village and confirm the second same-month submission is rejected. Admin soft-deletion of the village visit permits an authorized re-entry and does not purge old audit records.
9. Confirm prior month Action Plans, historic attendance and historical Specials remain readable.
10. Explicitly test offline queue behavior: the newly submitted visit is dated **when the server processes it**, not when the client captured it. Do not roll out until field teams accept this rule.
11. Confirm out-of-assignment submissions are credited to the submitting DA while original village ownership is unchanged. Test dashboard rollups under Admin/PC/DA permissions.
12. Only after checks pass, roll out to production and verify `/healthz` returns `2026.27.25`.

**Important:** This package has static/syntax validation, but has not passed Flask/PostgreSQL end-to-end testing in this environment.
