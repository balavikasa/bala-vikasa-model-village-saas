> CI/deployment addendum: see `DEPLOYMENT_AND_CI_FIX_2026-10-27.md`. The release fingerprint is **2026.27.19**.

# Release notes — 27 October 2026 — 5 requested changes

## Deliverables

1. **Attendance only:** DA menu, PWA shortcut and new-entry actions no longer offer Specials. POST `/api/v1/specials` and old committee-level POST `/api/v1/attendance` return 410. Historical Specials rows and existing committee-level Attendance remain untouched.
2. **One village visit:** DA chooses a village and enters each active, pending and scheduled committee's attendance, member selections, new members, remarks, early/postponed reasons, etc. A single POST `/api/v1/attendance/village` creates a `VillageAttendanceVisit` parent and many `AttendanceEntry` children, sharing one photo/GPS. The village Report view combines committee entries into one report. Individual committee records remain for previous queries and export. **All active committees must have executable Attendance schedules to submit a combined visit**; previously completed committees are displayed but cannot be resubmitted.
3. **Location permission:** DA application automatically requests GPS/browser permission; it captures location without an extra button after permission. If location is denied/unavailable, a dialog gives retry and settings instructions. GPS is required at submit and is rejected if older than two minutes. Browsers cannot switch on disabled phone GPS or override permission denial.
4. **Compact maps:** Admin/PC/DA map popups show village, current status, assigned DA, committees, last visit and a photo. The point represents the **last GPS submitted**, not live ongoing tracking.
5. **Plans carry forward:** Current/future months obtain missing attendance plan occurrences from the latest scheduled prior month, carrying the schedule day and notes without duplicating committee/month rows. End-of-month dates clamp correctly for February and recover original anchors in longer months. Manual/Excel imports override recurrence. Plans with **no historical assigned date** still require a PC to provide their initial schedule. An existing human-created blank slot is not silently overwritten.

## PostgreSQL deployment (migration, do not replace existing DB)

Back up the current production database and the photo uploads folder. Deploy the updated code, set the existing environment configuration and run:

```sh
python -m flask --app wsgi db upgrade
```

New Alembic migration `20261027_0003_village_attendance.py` adds `village_attendance_visits` and nullable `attendance_entries.village_visit_id` without dropping legacy tables. Do not apply the uploaded October snapshot over a newer live database. Existing service worker caches refresh on version change. Test with a non-production database before production.

## Manual acceptance tests (requires Flask and PostgreSQL)

- [ ] DA login prompts for location the first time; with permission already granted, location is retrieved automatically; denied permission keeps submission blocked and shows help.
- [ ] DA Action Plans shows one village-level card, not multiple committee-specific GO buttons.
- [ ] Attendance form loads *all* active assigned village committees and their members; one image and GPS are shared. Submit creates exactly one new village visit, `n` committee rows and preserves audit relationships. Idempotent retry does not create a second visit.
- [ ] Missing/unscheduled committee gives a clear PC scheduling message (no fabricated monthly schedule); completed committee is not resubmitted.
- [ ] DA offline entry queues exactly one submission with one photo blob and syncs on reconnect; stale old Specials queue entries report permanent 410 errors instead of infinite retries.
- [ ] PC schedules an initial month, opens next month and confirms dates carry. If scheduled on January 31, February clamps to 28/29 and March goes back to 31. Manual edits and imported date overrides remain authoritative.
- [ ] Admin/PC/DA maps show compact popup and role-scoped location/photo. No active GPS evidence means marker absent until GPS or village master coordinate exists.
- [ ] Reports show one combined village record and committee-wise drilldown; historical attendance/Specials reports still viewable. Deleting group from Admin moves records to Recycle Bin without deleting shared image from another active record.

## Verification status

`scripts/validate_release.py` checks Python compile, JavaScript parse, Jinja syntax, offline PWA assets, migration table names and static workflow tokens. It does **not** run the Flask/SQLAlchemy integration tests in an environment lacking those dependencies. Verify on staging with a real PostgreSQL database before treating this as production-ready.
