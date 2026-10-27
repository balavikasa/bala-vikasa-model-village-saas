# Admin password reset hotfix - Model Village 2026.27.21

## Purpose

PCs and DAs are staff profiles. Their sign-in passwords belong to the corresponding linked `User` account, not the `PC` or `DA` table. The former Master Data interface did not expose this distinction or provide a direct password reset in the PC/DA profile list.

## Workflow

1. Log in as a system administrator.
2. Open **Master Data** and choose **Project Coordinators** or **Development Agents**.
3. Find the employee and select **Reset password**.
4. Enter and confirm the new password (6-128 characters); click **Update password**.
5. Give the new password to the employee through an appropriate private channel. Ask them to sign out and sign back in. The old password will no longer work for a new login.
6. The same action is available for PC/DA records in **Users**.

If a PC/DA row displays **No login linked**, that staff profile does not have an active, non-deleted linked `User` record. Use the Users section to create or restore their login account first. Resetting a password does not automatically enable a disabled login account; Admin can enable that separately under Users.

## Security and data safety

- Admin-only API: `POST /api/v1/admin/pcs/{id}/reset-password`, `POST /api/v1/admin/das/{id}/reset-password`, and `POST /api/v1/admin/users/{id}/reset-password` for DA/PC users.
- Passwords are hashed using the existing `User.set_password()` implementation; no password strings or hashes are returned to the browser or written to the audit record.
- A reset records an `UPDATE` audit entry with a `password_reset` flag and the change timestamp.
- Clears the target's failed-login counter and temporary login lockout.
- Rejects weak (<6 characters), overlong (>128 characters), mismatched, or unchanged passwords.
- Does not change profiles, role assignments, committee data, attendance, or action plans.
- No database schema migration is required.
- Existing browser sessions may remain active until they expire or sign out; this hotfix does not implement global session revocation.

## Deployment verification

1. Run `python scripts/validate_release.py --require-runtime` and `ruff check .` in GitHub Actions.
2. Run `python -m pytest -q tests/test_admin_password_reset.py` and the full suite in CI.
3. Check `/healthz`: it should return `{"status":"ok","release":"2026.27.21"}`.
4. After deploying, refresh the installed PWA (service-worker version `2026.27.21-admin-password-reset`).
5. Use a staging PC and DA account to verify reset, old-password rejection, new-password login, and audit trail; test a missing-linked-account state.
6. Back up the production database before deploying code, even though this change does not require migration.

## Verification scope in this environment

- `compileall`: passed.
- `node --check` for Admin JavaScript: passed.
- Static release validation: passed.
- Full Flask/SQLAlchemy test runtime and Ruff could not be installed because this container cannot reach the Python package index. CI execution is still required.
