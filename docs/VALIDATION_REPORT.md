# Validation report

Generated: `2026-08-26T04:16:28+00:00`

This report distinguishes executed checks from checks skipped because the build environment lacks runtime dependencies. A skip is not represented as a pass.

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
| PC persisted cluster source | **PASS** |  |
| Thirteen-table Alembic migration | **PASS** |  |
| 44px touch targets and adaptive breakpoints | **PASS** |  |
| Workbook opens and profiles | **PASS** | 13 sheets |
| Exact production master-data row counts | **PASS** | PMs=2, PCs=2, DAs=9, Villages=42, Committees=351, Committee_Members=2433, Action_Plans=351, Attendance_Entries=0, Specials_Entries=0, PC_DA_Map=9, Recycle_Bin=0 |
| Flask application factory and in-memory schema | **PASS** |  |
| Pytest suite | **PASS** | ..............................................                           [100%] 46 passed in 3.03s |

## Summary

- PASS: 26
- FAIL: 0
- SKIP: 0

## Reproduce the full runtime gate

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate_release.py --require-runtime
```
