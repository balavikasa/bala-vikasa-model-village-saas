# Model Village SaaS: DA attendance release verification and CI repair

## Why the website looks unchanged

GitHub `main` has version `883a8e76f938fba1a1db30ea511e42d3981504c1` (Update V.0.0.3), and the failing GitHub Actions run 40482654414 checks that commit. The `.github/workflows/ci.yml` workflow only tests code: it has no deployment step. A Git push or a new ZIP does not, by itself, replace the running Coolify containers. The screenshot of `/map` still shows the older, taller village popup. This could indicate an older deployment and/or a cached PWA; the screenshot cannot establish which.

## Changes in this repair package

- Existing one-village attendance form and database migration retained: `/field/attendance`, `/api/v1/attendance/village`, `20261027_0003_village_attendance.py`.
- Replaced outdated DA work-queue regression test to expect **one action per village**, suppress legacy Specials and previous-month tasks from the current-month execution queue, and test Today/Pending/Upcoming independently across villages.
- Expanded schema tests to require **14 tables**, the new `village_attendance_visits` table, nullable legacy-compatible `attendance_entries.village_visit_id`, and its foreign key.
- Added explicit deployment identity: `GET /healthz` now returns `{"status":"ok","release":"2026.27.19"}`; responses include `X-MV-Release: 2026.27.19`.
- Updated service worker cache to `2026.27.19-village-attendance-ci` to replace stale assets after deployment.
- Village attendance page now immediately identifies unscheduled committees and disables submission when no executable plan exists. This avoids the illusion that a blank October plan can be submitted.

## Why October 2026 still needs planning

The user-supplied **Action_Plans_2026-10 (1).xlsx** contains exactly 361 rows for 43 villages / 361 committee IDs. Every row is `Draft`, the activity `Type` is blank, and `Assigned Date` is blank. No village is currently ready for attendance submission from this export. A PC or Admin must assign executable **Attendance** dates using the existing Action Plan editor or the exported/imported workbook. The system must not invent those dates or overwrite deliberate blank records.

The PC/Admin Action Plans grid deliberately remains committee-level so import/export, overrides, and committee-level statuses are retained. The **DA Attendance workflow** is where all those committees are combined into one village-level submission, including one photo and GPS fix. Check the new DA screen, not only the PC/Admin planning grid.

## Deployment steps (non-production staging first)

1. Preserve the current PostgreSQL backup **and** the uploaded-photo directory. Do not restore an older database dump over newer records.
2. Commit/push this package to the GitHub deployment branch and ensure CI checks complete (including full pytest, lint, and migration smoke test). The current GitHub connector in this conversation is **read-only** (403 on branch creation), so the ZIP must be pushed by a repository maintainer.
3. In Coolify, select the correct GitHub repository/ref and **redeploy/rebuild** the service. If deployment is based on an image, make sure it builds from this new commit, not an old cached image/tag.
4. Run the Alembic migration in the app container, using its existing DATABASE_URL and secrets:
   ```bash
   python -m flask --app wsgi db upgrade
   ```
5. Visit `https://mv.balavikasa.digital/healthz` and confirm `release` equals `2026.27.19`. If it says only `status: ok`, or shows a different release, the backend is not yet running this package.
6. Log in as a **DA**, open **Attendance** directly (`/field/attendance`), and confirm the heading says **Village Attendance** and its text says *One village · All scheduled committees · One photo · One GPS location · One submission.* Pick a village to see committee cards. If its committees are unscheduled, it correctly warns that PC scheduling is required.
7. Log in as Admin/PC, inspect `/map` and verify the **compact** popup (village name, status, small photo, two quick facts, location source, link). Action Plan **Admin/PC** views are still committee-by-committee, by design.
8. Once production is verified, have DAs synchronize queued offline submissions **before** clearing any device's site storage. Clearing site data can delete unsynced IndexedDB records. A hard refresh and new service-worker activation normally suffice.

## Validation status

`python scripts/validate_release.py` passes all static contract checks. `python -m compileall -q app tests` and `node --check` on all 20 JavaScript files pass. Flask dependencies could not be installed in this environment because the package index was unreachable. Therefore **full pytest, Ruff lint, and a live PostgreSQL migration have not been executed here**, and CI passing must be confirmed after a maintainer pushes this repair.
