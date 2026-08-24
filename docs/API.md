# API Overview

All APIs use the authenticated Flask session. State-changing requests require CSRF protection.
Authorization is enforced server-side through role checks plus object scoping.

## Session / scoped data

- `GET /api/v1/auth/csrf` — fresh CSRF token.
- `GET /api/v1/me` — authenticated user/profile context.
- `GET /api/v1/villages` — visible villages.
- `GET /api/v1/villages/<id>/committees` — visible committees for a village.
- `GET /api/v1/committees/<id>/members` — enabled master Committee Members.
- `GET /api/v1/committees/<id>/action-plans` — scoped plan occurrences; supports Type, executable,
  pending and month filtering.
- `GET /api/v1/directory` — role-scoped Villages/DAs/PCs/PMs.
- `GET /api/v1/monitoring/summary|series|map` — role-scoped monitoring data.

## DA field submission

- `POST /api/v1/attendance` — DA only.
- `POST /api/v1/specials` — DA only.
- `GET /api/v1/attendance|specials` — scoped entry history.
- `GET /api/v1/photos/<attendance|specials>/<id>` — scoped evidence photo.

Each write includes unique `client_submission_id`; accepted replay returns the existing row.

The server validates Village → Committee → ActionPlan ownership and plan type. Attendance/Specials
status is calculated by the server; clients do not choose it.

## Monthly Action Plans

Page/API endpoints:

- `GET /action-plans`
- `GET /api/v1/planning/month?month=YYYY-MM`
- `POST /api/v1/planning/plans` — Admin/PC, single plan occurrence.
- `PATCH /api/v1/planning/plans/<id>` — Admin/PC, unlocked occurrence.
- `POST /api/v1/planning/prepare-next-month` — Admin/PC.
- `GET /action-plans/export.xlsx?month=YYYY-MM` — Admin/PM/PC.
- `POST /api/v1/planning/import/preview` — Admin/PC.
- `POST /api/v1/planning/import/confirm` — Admin/PC.

PM can inspect/export but cannot import or mutate.

## Reports

- `GET /reports`
- `GET /api/v1/reports?month=YYYY-MM&type=&status=`
- `GET /reports/plan/<id>` — full View detail.
- `GET /reports/export.xlsx?...` — scoped Excel export including Committee Member Name and Visit
  Designation.

## Admin master-data transfer

Admin only:

- `GET /admin/data-transfer`
- `GET /admin/data-transfer/export.xlsx?resource=<key>`
- `POST /api/v1/admin/data-transfer/preview`
- `POST /api/v1/admin/data-transfer/confirm`

Resources: PMs, PCs, DAs, Villages, Committees and Committee Members. Imports are staged, previewed,
revalidated and committed atomically. Omission does not delete.

## Admin lifecycle API

Registry-driven Admin endpoints under `/api/v1/admin/...` retain add/edit/move/enable/disable/delete/
restore, user management, audit log and recycle-bin behavior. See the generated route inventory for
the concrete endpoint list.
