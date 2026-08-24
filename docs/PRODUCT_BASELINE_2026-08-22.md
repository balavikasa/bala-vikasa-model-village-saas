# Model Village SaaS — Locked Product Baseline

Date: 2026-08-22

This document records the product decisions approved for the rebuild. In case of conflict, use this
precedence:

1. Explicit client corrections/approvals from the rebuild discussion.
2. `docs/reference/Model-Village-Project-Documentation.md`.
3. Normalized Model Village master data.
4. `docs/reference/model-village-dashboard-prototype.html` for visual language and interaction direction.
5. Older generated application code.

## Product

A mobile-first field-operations SaaS for Bala Vikasa's Model Village Program 2026–27. The product
plans committee visits monthly, lets DAs execute field work with evidence, and gives PC/PM/Admin
role-scoped monitoring, reports, maps and directory drill-downs.

Master-data baseline: 2 PMs, 2 PCs, 9 DAs, 42 villages, 351 committees and 2,433 committee members.

## Role hierarchy and scoping

- Admin: global administrative role. Full master-data/user lifecycle, audit, recycle bin and imports.
  Admin sees disabled records but does not use DA field submission screens.
- PM: global read-only monitoring across both clusters.
- PC: sees only DAs/villages below their own PC profile and manages their monthly Action Plans.
- DA: sees only assigned villages and executes assigned monthly Attendance/Specials plans.
- Cluster is persisted only on `PC.cluster`; DA and Village inherit it through relationships.

Every protected object read is server-scoped. Client-supplied IDs never grant access.

## Mobile-first navigation

Phone navigation is role-specific:

- DA: Home · Plans · Entry · Reports · Map
- PC: Home · Plans · Team · Reports · Map
- PM: Home · People · Plans · Reports · Map
- Admin: Home · Plans · Reports · Map · Admin

Tablet/desktop use a side rail and wider bento/detail layouts. The visual system is restrained
Bento Grid + Minimalism, preserving the prototype's navy/paper/saffron/green/clay language.

## Monthly Action Plans

A monthly Action Plan is one committee occurrence for one calendar month.

- Action Plans open on the program's current month automatically.
- PC can switch previous/current/next month.
- A plan can be a Draft with a pre-filled Type and no Assigned Date.
- It becomes executable only when `plan_month`, `plan_type` and `assigned_date` are all present.
- PC may edit a single plan in-app or use Excel for bulk planning.
- Completed plans, passed due dates and past months are immutable to PC planning edits.
- A past due plan without submission is `Failure`; a later DA submission becomes `Postponed`.

### Export → edit → preview → confirm

PC selects the month and exports an `.xlsx` sheet scoped to their own committees. Stable IDs and
context columns are locked. Type/Assigned Date/Notes are editable.

Import never writes immediately:

1. Upload workbook for the selected month.
2. Validate stable IDs, scope, dates, types and immutable rows.
3. Preview New / Changed / Unchanged / Error rows.
4. Confirm only when the preview is valid.
5. Apply atomically and audit the import.

An exported planning workbook is bound to the user who exported it.

### Prepare Next Month

`Prepare next month` creates the following month's committee occurrences, copying Type and Notes
from the source month but intentionally not copying Assigned Date. This lets the PC set fresh dates
without recreating committee structure.

## DA Attendance

Flow: Village → Committee → assigned current-month Attendance plan.

Server status:

- visit date before assigned date → Early; Reason required
- same date → On-time; Reason hidden/not required
- after assigned date → Postponed; Reason required
- passed assigned date with no submission → Failure (derived, no fake entry)

Attendance stores live Male/Female counts, server-computed Total, New Members Count, photo evidence,
GPS and optional remarks. Master Male/Female/Total are looked up from Committee Members.

### Visit Designations → Committee Member Name

After Village + Committee is selected, the app loads that committee's enabled master members grouped
by President / Vice President / Secretary / Member.

- zero matching names: designation unavailable
- exactly one matching name: tapping the designation selects that name directly; no dropdown
- more than one matching name: tapping opens a searchable multi-select bottom-sheet/dialog

The selected master member IDs are saved with name/designation/gender snapshots so historical reports
do not change if master data is edited later. This is not a full person-by-person attendance register;
live Male/Female counts remain independent.

## DA Specials

Flow: Village → Committee → assigned current-month Specials plan.

Current Special name follows the Committee until a future Specials catalogue is supplied. Scope is
exactly one of `Under GP` or `Under VDC`. Participants, status/reason, photo, GPS and notes are stored.

## Reports

The report list is intentionally concise:

Date · DA · Village · Committee · Type · Status · View

No map/photo/GPS/member-name clutter is shown in the list. `View` opens the full report detail with
assignment details, attendance/special data, selected Committee Member Names grouped by designation,
reason, image evidence, GPS and map.

Excel report export includes Committee Member Name and Visit Designation.

## Maps and profiles

Map data is role-scoped. Phone UI supports Map/List switching. Village popups show operational status,
last visit/evidence where available and a View action.

Directory/profile drill-downs exist for PM, PC, DA and Village within the caller's allowed scope.

## Admin bulk master-data transfer

Admin can Export → edit → Validate/Preview → Confirm for PMs, PCs, DAs, Villages, Committees and
Committee Members. Omission never deletes a row. Relationship changes are previewed as `Moved` and
audit-logged. Users/passwords are intentionally not bulk-imported. Monthly Action Plans use their
dedicated PC/Admin planning transfer flow.

## PWA/offline

DA submissions use WebP photo compression, device GPS, stable `client_submission_id`, IndexedDB
outbox storage and retry/sync. Server idempotency prevents duplicate accepted submissions.
