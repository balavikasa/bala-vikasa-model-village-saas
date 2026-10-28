# Bala Vikasa Model Village - DA/PC Login Recovery (2026-10-27)

## What the supplied evidence proves

1. Flask received repeated `POST /login` requests that returned HTTP 200, consistent with the rendered invalid-credentials login page. Those requests were not HTTP 500 application crashes.
2. The supplied PostgreSQL server log shows the database continuing to run, with no authentication-related SQL error during the October 27 login attempts.
3. The separately supplied October 26 PostgreSQL backup contains a D.Ramesh DA profile linked to a User account; that User account's email differs from the email typed in the screenshot (`dramesh@balavikasa.org`). The screenshot address did not appear among the snapshot's User emails. Production might have changed since that snapshot.

The evidence does not prove the current password, active account state, or whether a later Admin reset changed the live account.

## First: verify deployed version

Open `https://mv.balavikasa.digital/healthz`. Version `2026.27.22` indicates that the earlier Admin login-identifier reset UI release is running; an older version means you must first deploy the intended version. An HTTP 200 /readyz proves database reachability, *not* that a particular staff login is valid.

## Recommended no-code fix (existing v2026.27.22 Admin UI)

1. Sign in with an existing System Administrator account (do not log in as the DA).
2. Open Master Data > Development Associates > D.Ramesh > Reset password.
3. Read the **Login email** and **Login mobile** fields. They are not necessarily the same as the DA staff contact fields.
4. If the desired email is `dramesh@balavikasa.org`, enter it in **Login email**, unless it belongs to another User. Keep or correct the registered mobile, set and confirm a NEW password, check *Enable account* only if an authorized administrator intends to enable a disabled account, and click Update password.
5. Confirm that the server shows a successful save. Test in a private browser window with the exact **Login email** that was saved and the new password. Do not post credentials or hashes into chat/logs.
6. If the save fails, note the exact HTTP status and red error message in the Admin UI. Do not repeatedly retry a failing login: after five bad attempts this app temporarily locks the account for 15 minutes.

## Server-side inspect and repair, if the Admin UI cannot complete the update

This helper is provided at `scripts/repair_staff_login.py`. Copy it into the `scripts/` directory of the same source version deployed in Coolify, deploy that version, then open a terminal *inside the Flask application container* with the existing `DATABASE_URL` configured.

**Dry-run (read-only):**

```bash
python scripts/repair_staff_login.py --role da --staff-id 2 --login-email dramesh@balavikasa.org
```

The ID 2 mapping is visible in the earlier backup and Admin screenshot. Confirm the script prints the expected staff name and linked User before applying any change. Do not assume staff IDs are identical if the production records have changed.

**Interactive repair (changes ONE existing linked User only):**

```bash
python scripts/repair_staff_login.py --role da --staff-id 2 --login-email dramesh@balavikasa.org --apply
```

This asks you to confirm `RESET DA 2` and securely enter/confirm the new password in the terminal. It updates that linked User's login email (if changed), password hash, unlock state, and audit trail in one database transaction. It **does not** create an account, change any other user, or print/log the password. It does not enable a disabled account unless you explicitly include `--enable`.

**To repair a PC:** replace `--role da --staff-id 2` with that PC's verified role and staff ID.

### Safeguards and notes

- Run from the application container, not the separate PostgreSQL container.
- Make a fresh PostgreSQL backup before running `--apply`.
- The helper refuses to run without a PostgreSQL `DATABASE_URL` and refuses duplicate login emails or mobiles.
- Run as an authorized operator in a private terminal; the output includes staff login identifiers.
- Do **not** pass passwords as CLI flags, paste hashes into SQL, or set all users to a shared password.
- The helper is a targeted recovery tool, not an endpoint exposed to the public web.
- If the linked User is missing or deleted, do not force-create an account from this script. Review the Admin Users data and profile association first.
- After repair, use an incognito tab to log in; success returns an HTTP 302 redirect rather than 200 with the same error page.

## Optional read-only SQL confirmation

Run in a PostgreSQL console as an authorized administrator:

```sql
SELECT d.id AS da_id, d.full_name, u.id AS login_user_id,
       u.email AS login_email, u.mobile AS login_mobile,
       u.role, u.is_enabled, u.is_deleted,
       u.failed_login_count, u.locked_until, u.password_changed_at
FROM das AS d
LEFT JOIN users AS u ON u.da_id = d.id
WHERE d.full_name = 'D.Ramesh';
```

This does not expose password hashes. The query assumes a staff profile named exactly `D.Ramesh`; adapt the filter if production uses a different spelling.

## If failure persists after a confirmed reset

Verify that the Admin's save and the login attempt point to the same application release and database. Check the matched User's updated `password_changed_at`, email/mobile, enabled/deleted state, and lock expiry in the application database. The uploaded **PostgreSQL** logs alone do not record invalid passwords; a generic failed login can legitimately return HTTP 200 without a database error.
