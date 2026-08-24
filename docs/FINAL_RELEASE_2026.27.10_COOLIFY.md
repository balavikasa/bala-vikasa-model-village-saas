# Historical release note — superseded by 2026.27.11 PostgreSQL

# Final Coolify/Hostinger Release — 2026.27.10

This release prepares the tested Model Village SaaS for Hostinger DNS + Hostinger VPS + Coolify.

Changes:
- adds `/healthz` and database-aware `/readyz`;
- adds a Docker health check for Coolify/Traefik readiness;
- adds `coolify.env.example`;
- adds `.dockerignore` to prevent secrets/local DB state entering images;
- renames Compose to `docker-compose.local.yml` to avoid accidental production host-port conflicts;
- corrects proxy/session environment names in the local Compose helper;
- adds persistent-upload deployment guidance;
- adds safe empty-target SQLite -> production database migration helper;
- adds public HTTPS smoke-test script;
- adds Hostinger DNS, firewall, Coolify, MySQL, backup, restore and rollback documentation.

Recommended production architecture:
Dockerfile Application + standalone Coolify PostgreSQL resource + named uploads volume.
