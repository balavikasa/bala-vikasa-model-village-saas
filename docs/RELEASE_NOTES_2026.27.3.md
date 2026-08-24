# Release Notes — 2026.27.3

This is the first full SaaS rebuild aligned to the approved Model Village documentation, dashboard
prototype and the client corrections made during the rebuild discussion.

## Major product changes

- Mobile-first Bento/Minimalist shell for DA, PC, PM and Admin.
- Role-specific phone bottom navigation and desktop/tablet rail.
- Monthly PC Action Plan occurrences with immutable monthly history.
- Current-month Action Plan landing page with program date/time.
- Single-plan edits plus Excel Export → Validate/Preview → Confirm bulk planning.
- Prepare Next Month copies structure, Type and Notes without copying dates.
- DA Attendance/Specials requires an assigned executable monthly plan.
- Correct Early / On-time / Postponed / Failure semantics.
- Visit Designation → Committee Member Name master lookup:
  - one person selects directly;
  - multiple people open a searchable tick picker.
- Attendance stores selected master member IDs plus immutable snapshots.
- Reports are concise and end in View; full evidence/map/member detail lives behind View.
- Role-scoped Village Map with phone Map/List mode.
- PM/PC/DA/Village profile drill-downs.
- Admin generic master-data Excel Export → Preview → Confirm transfer.
- Admin sees disabled records; non-Admin roles do not.
- Admin does not impersonate DA field submissions.
- Explicit approved-prototype Village coordinate backfill command.
- SQLite development and MySQL production architecture retained.
- PWA/WebP/GPS/offline queue/idempotent replay retained and integrated with the rebuilt workflow.

## Migration behavior

The existing 351 pre-rebuild ActionPlan rows are preserved as `plan_month=NULL` legacy/template rows.
They are not executable. PC/Admin create real monthly Action Plan occurrences through the new
planning workflow.

No existing PM/PC/DA/Village/Committee/CommitteeMember data is intentionally deleted by migration.

## Important upgrade rule

Install this release into a new folder first, copy your existing database/uploads into it, back up the
database, run migrations, then verify all four roles before replacing the old application folder.

See `UPGRADE_2026.27.3.md`.
