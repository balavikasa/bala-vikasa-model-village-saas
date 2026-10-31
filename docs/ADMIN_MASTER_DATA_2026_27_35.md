# Bala Vikasa Model Village — Admin Master Data corrections v2026.27.35

## Why this release exists

Admin must control the creation, edits and assignment relationships of Program Managers, Project Coordinators, Development Agents, Villages, Committees, Committee Members and Users. The previous generic Add Record dialog had two important gaps: PM→PC assignment did not exist in the database, and creating a staff profile did not create their linked login account. Required relationships silently selected the first option, and committee choices did not identify villages. These problems could lead to wrong assignments and unusable staff logins.

## Changes

1. **Manage data selector** is prominent in the Admin Master Data toolbar. **Add** is contextual (e.g. Add Village, Add Development Agent).
2. Assignments use searchable dropdowns, include a parent name/context and ID, and use an explicit required placeholder instead of assigning the first record silently. Options load across all API pages rather than stopping at 500. Missing parent data shows a clear create-parent action.
3. Assignment chain: **PM → PC → DA → Village → Committee → Committee Member**. PC.pm_id is optional to preserve old data; newly assigned PMs appear in the PC table and editor.
4. PM/PC/DA can have a linked login created in the **same transaction** as their staff record or later from the same staff Edit dialog. Separate login email/mobile are permitted. The password must be 12–128 characters and is hashed; it is not returned or logged. Login creation is strictly optional and only done if the Admin selects it.
5. **Users** creation/edit is role-aware: PM shows PM profile, PC shows PC, DA shows DA, admin has no attached profile. Switching roles clears unrelated mappings.
6. PM staff login password reset is available in PM and Users screens; existing PC/DA password resets remain.
7. Server rejects assignments to missing/deleted/disabled parents with a specific validation message. Duplicate login identifiers result in an atomic rollback, not orphan staff records.
8. No existing staff, village, committee, User or attendance rows are automatically changed. PM assignments start empty until Admin assigns them.

## Deployment / migration (required)

**This release has a database migration.** Back up PostgreSQL and uploads, then deploy the v2026.27.35 source and run:

```
python -m flask --app wsgi db upgrade
```

This runs revision `20261031_0005`, adding nullable `pcs.pm_id` and its foreign key/index. **Do not restart application workers against the new model until this migration succeeds.** Keep previous app version ready for rollback. Existing PC rows keep `pm_id=NULL` (not auto-assigned). Historical reports and attendance do not change.

For staff workflows use `/admin` → Master Data → Manage data:

1. Program Managers → Add Program Manager (with optional linked login).
2. Project Coordinators → Add Project Coordinator → Cluster → optionally choose Assigned Program Manager → optional linked login.
3. Development Agents → Add Development Agent → select Assigned Project Coordinator → optional linked login.
4. Villages → Add Village → select Assigned Development Agent.
5. Committees → Add Committee → select Village.
6. Committee Members → Add Committee Member → select Committee (name and village shown).
7. Users → Add User → choose role → select corresponding staff profile and set password. Or use Edit on a staff record without linked login to provision it there.

Reassignment of DA/Village records with historical attendance may require acknowledgement and must be checked carefully. Staff contact fields and User login identifiers are distinct unless Admin deliberately sets matching details.

## Safety and limits

- All new write APIs remain under `/api/v1/admin` and retain the Admin role guard, authenticated session/CSRF handling and audit logs.
- Optional `PC.pm_id` is an **administrative assignment**; it does not by itself change PM’s existing global read scope, reporting permissions or ownership logic. Changes to authorization should be a separately tested release.
- Staff password reset / account creation should be tested first with staging accounts. Do not send passwords via chat or log them.
- Full Flask/PostgreSQL integration is still required in GitHub CI and staging. The local workspace did not have Flask and could not install its dependencies.

## Acceptance checks

- Create PM, PC assigned to PM, DA assigned to PC, Village assigned to DA, Committee assigned to Village, Member assigned to Committee; verify new records in every Master Data table.
- Create PM/PC/DA with linked login; check correct Role and profile ID, mobile/email sign-in, then reset password from Master Data.
- Create a staff profile without login, edit it and provision login afterwards.
- Select different roles under Users; confirm only relevant profile can be selected.
- Select a committee named "Water" in two villages; confirm village label prevents the wrong link.
- Confirm duplicates, unknown/disabled parent IDs, missing required assignments and password mismatch display clear errors and create **no partial records**.
- Check Admin desktop/mobile create/Edit modal alignment; ensure add flow can access more than 500 option rows.
- Test login of DA and PC and ensure their assigned villages remain visible. Verify attendance, analytics and reports unchanged.
