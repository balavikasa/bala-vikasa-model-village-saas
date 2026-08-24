# Final Release — 2026.27.9

Bala Vikasa Model Village SaaS / PWA 2026–27

## Included product behavior

- Roles: Admin, PM, PC, DA.
- Admin: global administration, master data, users, audit, Recycle Bin, reports and imports.
- PM: global read-only monitoring across both CSRB and PDTC.
- PC: own-team scope with monthly Action Plan management and Excel transfer workflow.
- DA: assigned-village field execution for Attendance and Specials.
- DA `/` and `/overview` redirect to `/field/attendance`.
- Reports use list/card → View detail; maps are on detail screens.
- Soft deletion uses the Recycle Bin; configured retention is 10 days.
- Attendance/Specials evidence supports GPS and WebP image processing.
- Mobile/PWA shell includes offline queue state and direct logout.

## Validation evidence

The accepted local UAT run recorded:

- 38/38 pytest checks passing.
- Role-wise browser evidence for Admin, PM, PC and DA.
- Desktop and 375×667 mobile screenshots.
- RBAC checks.
- Leaflet rendering checks.
- PC Action Plan Excel export/import preview/confirm checks.

See `docs/qa/Bala_Vikasa_Model_Village_Final_UAT_QA_Report_2026-27.pdf`.

## Upgrade from the accepted local database

Do not overwrite your accepted database or `.env`.

1. Back up `instance/model_village.db` and `.env`.
2. Extract this release into a new folder.
3. Copy your existing `.env` into the new folder.
4. Copy your existing `instance/model_village.db` into the new `instance/` folder.
5. Activate the virtual environment and install dependencies.
6. Run `python -m flask --app wsgi db upgrade`.
7. Run `python -m ruff check .`.
8. Run `python -m pytest`.
9. Start with `python -m flask --app wsgi run --debug --host 127.0.0.1 --port 5000`.
10. Update/unregister the old service worker once if a browser still uses stale UI assets.

## Production

Use MySQL, a strong `SECRET_KEY`, HTTPS, `SESSION_COOKIE_SECURE=1`, and your deployment's proxy/TLS
settings. Never deploy the local test credentials or a development `.env`.
