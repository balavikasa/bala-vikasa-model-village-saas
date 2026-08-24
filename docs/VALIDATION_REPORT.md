# Validation report

Generated: `2026-08-22T05:28:51+00:00`

This report distinguishes executed checks from checks skipped because the build sandbox lacks
runtime dependencies. A skip is not represented as a pass.

| Check | Result | Detail |
|---|---:|---|
| Python bytecode compilation | **PASS** |  |
| JavaScript syntax | **PASS** | 17 files checked |
| Jinja template syntax | **PASS** | 16 templates checked |
| PWA manifest contract | **PASS** |  |
| Install icon dimensions | **PASS** |  |
| Centralized scoping | **PASS** |  |
| Offline queue and Background Sync | **PASS** |  |
| IndexedDB outbox | **PASS** |  |
| WebP camera compression | **PASS** |  |
| Attendance business rules | **PASS** |  |
| Failure projection | **PASS** |  |
| Monthly planning transfer | **PASS** |  |
| Master-data preview transfer | **PASS** |  |
| Report member detail | **PASS** |  |
| Admin move/recycle lifecycle | **PASS** |  |
| Leaflet monitoring | **PASS** |  |
| Three.js overview | **PASS** |  |
| Plotly Dash mount | **PASS** |  |
| Server attendance status values | **PASS** |  |
| PC-only persisted cluster source | **PASS** |  |
| Thirteen-table Alembic migration | **PASS** |  |
| 44px touch targets and adaptive breakpoints | **PASS** |  |
| Workbook opens and profiles | **PASS** | 13 sheets |
| Expected master-data row counts visible | **PASS** | README=35, DAs=9, Villages=42, Committees=351, Committee_Members=2433, Action_Plans=352, Attendance_Entries=2, Specials_Entries=2, PMs=3, PCs=3, PC_DA_Map=10, RBAC_Permissions=6, Recycle_Bin=2 |
| Framework runtime and pytest suite | **SKIP** | missing environment dependencies: flask, flask_sqlalchemy, flask_migrate, flask_login, flask_wtf |

## Summary

- PASS: 24
- FAIL: 0
- SKIP: 1

## Reproduce the full runtime gate

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate_release.py --require-runtime
```
