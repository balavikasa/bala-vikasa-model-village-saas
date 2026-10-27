# Admin / DA / PC login access fix — 2026.27.22

## Observed symptoms

* The employee login screen shows `Email/mobile or password is incorrect.`
* Admin can open **Reset password**, but the dialog is overly wide, congested, and not responsive.

The login error does **not** reveal whether the typed email/mobile is present in the Users table. The application authenticates against `users.email` and `users.mobile`, not the separate `das` and `pcs` staff profile contacts. A password reset alone cannot correct an identifier mismatch.

## Changes

1. The reset dialog is capped at 520px, centered on desktop and in a compact single-column layout on narrow screens. Inputs are evenly spaced; the existing full-screen record editor styling does not affect it.
2. Admin sees the linked **login email**, **login mobile**, active/locked/disabled status, and a warning when the staff profile contact differs from the actual login account.
3. Admin may explicitly correct the linked account's login email/mobile **in the same operation** as resetting the password. A valid email or Indian mobile number must remain available for login.
4. Duplicate emails and equivalent Indian mobile numbers are refused; invalid values do not update the password. The action is restricted to Admin and DA/PC accounts.
5. A disabled linked account can be explicitly enabled by checking the control. Ordinary password resets do not silently re-enable disabled accounts. Lockouts are cleared on a successful reset.
6. Passwords remain hashed and are never written into audit records. The audit includes changed identifiers, status and a boolean reset marker.
7. Login checks handle both timezone-aware (PostgreSQL) and naive (SQLite) account lockout timestamps.
8. PWA cache and application release version increment to `2026.27.22`.

## Important admin verification steps

1. Back up your PostgreSQL database and uploads volume before deployment.
2. Deploy the new source, clear/reload the PWA, confirm `/healthz` reports `release: 2026.27.22`.
3. Sign in as Admin. Open **Master Data > Development Associates** or **Project Coordinators**.
4. Find the employee and click **Reset password**. Check the login email/mobile shown here. These are the actual account identifiers, which can differ from the profile email/mobile.
5. Set a new password, update the login identifier when needed, and explicitly enable the account if it is disabled.
6. Sign out and test login with the **exact linked login email/mobile** shown by the dialog and the new password.
7. If the row says **No login linked**, create/restore the correct role-linked User under **Users** first. A password reset cannot create a missing login account.
8. Test one DA and one PC on staging before production rollout.
9. Inspect Coolify application logs if login continues to fail. Never share plaintext passwords or hashes in tickets.

## Testing status

Python compilation, JavaScript syntax and static validation passed locally. New regression tests cover account identity changes, duplicates, disabled-account enablement, SQLite lockout timestamp behavior, and login using corrected credentials. These runtime tests **have not been run** here because Flask packages cannot be installed from the network. Run `python scripts/validate_release.py --require-runtime` and `ruff check .` in GitHub Actions before deployment.

**Database:** No schema migration is introduced by this patch. Existing accounts, password hashes, staff links, and records remain intact until Admin explicitly updates a selected account.
