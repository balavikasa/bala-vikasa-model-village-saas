# Hostinger Domain + Hostinger VPS + Coolify Deployment

Release: **2026.27.11-PostgreSQL-Coolify**

## Recommended production topology

```text
Internet
   |
Hostinger DNS
   |
   +--> modelvillage.example.com  A -> VPS IPv4
   +--> coolify.example.com       A -> VPS IPv4
                                    |
                              Coolify Proxy
                              (80 / 443)
                                    |
                          Flask + Gunicorn
                          container :8000
                           /            \
              named uploads volume      Coolify PostgreSQL
              /srv/app/uploads          internal :5432
```

Use a **Dockerfile Application + standalone Coolify PostgreSQL resource**.

Do not use `docker-compose.local.yml` as the production Coolify resource. It exists only for local
standalone Docker testing. In particular, publishing host port 8000 would conflict with a self-hosted
Coolify dashboard that uses port 8000 for direct access.

---

## 1. Hostinger DNS

Recommended:

- App: `modelvillage.YOUR_DOMAIN`
- Coolify dashboard: `coolify.YOUR_DOMAIN`

In Hostinger hPanel -> Domain -> DNS / Nameservers add:

| Type | Name | Points to |
|---|---|---|
| A | modelvillage | YOUR_VPS_IPV4 |
| A | coolify | YOUR_VPS_IPV4 |

If the application should use the root domain instead, point `@` and `www` to the VPS IPv4.

Remove conflicting A/AAAA/CNAME records for the same hostname. Only create an AAAA record if the VPS
actually has working IPv6 routing.

DNS changes can take time to propagate.

---

## 2. VPS firewall

Keep SSH access working before changing firewall rules.

For normal public operation:

- TCP 22: SSH; preferably restricted to trusted administrator IPs.
- TCP 80: public.
- TCP 443: public.
- PostgreSQL 5432: **do not expose publicly**.
- Application 8000: **do not expose publicly**; Coolify proxy reaches it on Docker networking.

Self-hosted Coolify initially also uses 8000/6001/6002 for direct dashboard/realtime/terminal access.
After the Coolify dashboard works through `https://coolify.YOUR_DOMAIN`, those direct public ports can
be closed at the provider firewall if your Coolify setup no longer needs direct-IP access.

---

## 3. Put this release in Git

Coolify works best with a Git repository.

From the extracted application folder:

```bash
git init
git add .
git commit -m "Model Village SaaS 2026.27.11 PostgreSQL Coolify release"
git branch -M main
git remote add origin YOUR_PRIVATE_GIT_REPOSITORY
git push -u origin main
```

Use a private repository for production.

---

## 4. Create the PostgreSQL resource first

Coolify:

1. Create Project: `model-village`.
2. Create Environment: `production`.
3. Create Resource -> Database -> PostgreSQL.
4. Select the same server/destination that the application will use.
5. Use database name `model_village`.
6. Use a dedicated application user and a generated strong password.
7. Keep public database access OFF.
8. Start PostgreSQL and wait until healthy.
9. Copy the **Internal URL** from the PostgreSQL resource.

Coolify currently shows internal PostgreSQL URLs in the form `postgres://user:password@container:5432/database`. This application normalizes that URL to SQLAlchemy's Psycopg 3 driver automatically.

Use the standard PostgreSQL resource. Coolify currently offers PostgreSQL 18, 17 and 16; use a pinned major version for production and do not change it without a verified backup and upgrade plan.

---

## 5. Create the application

Coolify -> Project `model-village` -> `production`:

1. New Resource -> Private/Public Git Repository.
2. Select this repository and branch `main`.
3. Build Pack: **Dockerfile**.
4. Dockerfile path: `/Dockerfile`.
5. Base directory: `/`.
6. Port Exposes: `8000`.
7. Do not create a host port mapping for 8000.
8. Set domain:
   `https://modelvillage.YOUR_DOMAIN`

When an `https://` FQDN is configured and DNS is correct, Coolify manages the reverse proxy and TLS
certificate.

The image includes a Docker `HEALTHCHECK` against `/readyz`; do not configure a conflicting dashboard
health check unless you intentionally remove the Dockerfile health check.

---

## 6. Environment variables

Open `coolify.env.example`.

In Coolify -> Application -> Environment Variables, add the same keys using production values.

Required:

- `FLASK_ENV=production`
- `SECRET_KEY=<strong random secret>`
- `DATABASE_URL=<Coolify PostgreSQL Internal URL>` (usually `postgres://...`)
- `TRUST_PROXY=1`
- `SESSION_COOKIE_SECURE=1`
- `UPLOAD_FOLDER=/srv/app/uploads`

Generate the Flask secret locally:

```bash
python -c "import secrets; print(secrets.token_hex(48))"
```

Do not put the secret in Git, Dockerfile, screenshots, tickets, or chat.

Suggested initial Gunicorn setting for a modest single-VPS deployment:

- `GUNICORN_WORKERS=2`
- `GUNICORN_THREADS=2`

Tune after observing RAM/CPU and request latency.

---

## 7. Persistent evidence uploads

Coolify -> Application -> Persistent Storage:

Create a **named volume**:

- Name: `model-village-uploads`
- Destination Path: `/srv/app/uploads`

This is required. Without persistent storage, field evidence images can disappear when the container
is replaced during a deployment.

Do not share this writable upload volume across multiple web replicas unless you first move evidence
storage to shared/object storage or implement a safe shared-filesystem design.

---

## 8. First deployment

Deploy the application.

Container startup runs:

```text
flask --app wsgi db upgrade
gunicorn --config gunicorn.conf.py wsgi:app
```

The container becomes healthy only after the app can execute a database `SELECT 1`.

Verify in Coolify:

- Deployment: successful
- Container: healthy
- `/healthz`: HTTP 200
- `/readyz`: HTTP 200
- Application logs: no migration/database error
- Public domain: HTTPS certificate valid

---

## 9. Production data: choose ONE path

### Option A — recommended for this project: migrate the accepted SQLite database

Do this before bootstrapping a new production Admin account. The target PostgreSQL application tables must be empty. The helper also reseeds PostgreSQL sequences after copying explicit SQLite IDs.

1. Back up the accepted local SQLite DB.
2. Copy it to the VPS with SCP.
3. Copy it into the running app container as `/tmp/model_village.db`.
4. In Coolify Application -> Terminal:

```bash
python scripts/migrate_sqlite_to_postgresql.py --source /tmp/model_village.db --dry-run
```

Review all table counts.

Then:

```bash
python scripts/migrate_sqlite_to_postgresql.py --source /tmp/model_village.db
```

The migration helper refuses to run if the target application tables are already populated.

If the accepted local installation contains uploaded evidence photos, copy the `uploads` directory
separately into the persistent `/srv/app/uploads` volume.

After migration, remove the temporary SQLite file.

### Option B — fresh database

1. Deploy migrations.
2. Run the bootstrap Admin script.
3. Use Admin Master Data import workflows to load approved production data.
4. Create real PM/PC/DA user accounts through Admin.
5. Do not use UAT/test user credentials in production.

---

## 10. Bootstrap the first Admin

If you did not migrate an Admin account, open Coolify -> Application -> Terminal:

```bash
python scripts/bootstrap_admin.py
```

Enter a real organization-controlled Admin email and a unique password of at least 12 characters.

Do not leave bootstrap passwords in Coolify environment variables after use.

---

## 11. Hostinger/Coolify domain verification

After DNS propagation:

```bash
nslookup modelvillage.YOUR_DOMAIN
```

It should resolve to the VPS public IPv4.

Then verify:

```bash
python scripts/coolify_smoke_test.py https://modelvillage.YOUR_DOMAIN
```

Expected:

```text
PASS Liveness
PASS Readiness
PASS Login
PASS Manifest
PASS Service worker
PASS Security headers
```

Then perform one real DA phone test:

1. Sign in as DA.
2. Attendance opens first.
3. Select assigned Village -> Committee -> assigned plan.
4. Capture GPS.
5. Upload a non-sensitive test image.
6. Submit.
7. Verify Report -> View -> image + GPS + map.
8. Repeat with the browser offline, queue one controlled test, reconnect, and verify exactly one sync.

---

## 12. Backups before production sign-off

Configure all three layers:

### PostgreSQL
Coolify PostgreSQL -> Backups:

- scheduled PostgreSQL backup at least daily;
- keep local retention;
- send a second copy to configured S3-compatible storage;
- run **Backup Now**;
- keep at least one off-server/S3-compatible copy;
- perform a test restore into a disposable PostgreSQL database.

Coolify PostgreSQL backups use `pg_dump` custom-format backups by default.

### Evidence uploads
Coolify Application -> Persistent Storage -> configure backup for the uploads volume. Keep an off-server
copy as part of the same recovery set as the database.

### Coolify itself
Back up the Coolify instance and separately save the Coolify `APP_KEY` outside the VPS. A Coolify
instance backup is not a backup of application volumes/databases.

A backup is not considered reliable until a restore test succeeds.

---

## 13. Deployment/rollback routine

Before each production deployment:

1. Verify latest PostgreSQL backup succeeded.
2. Verify latest uploads backup succeeded.
3. Deploy the new image.
4. Confirm `/readyz` returns 200.
5. Run the smoke test.
6. Test login and one read-only report.
7. Monitor Coolify logs.

If the application code deployment fails, use Coolify rollback to a locally available previous image.
If a database migration changes schema/data, application rollback alone may not be sufficient; use the
migration-specific rollback/recovery plan and verified database backup.

---

## 14. Production security checklist

- HTTPS only.
- `FLASK_ENV=production`.
- `TRUST_PROXY=1`.
- Strong unique `SECRET_KEY`.
- Database remains private/internal.
- Uploads are persistent and backed up.
- No `.env` in Git.
- No production passwords in Docker image.
- Admin test accounts removed/disabled.
- SSH restricted where practical.
- Coolify dashboard protected with a strong account and MFA if available.
- Database and upload restore tested.
- Hostinger/VPS provider firewall configured before public launch.
