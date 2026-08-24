# PostgreSQL + Coolify Production Release — 2026.27.11

This release makes PostgreSQL the production database for the Model Village SaaS.

Key changes:
- replaces PyMySQL with Psycopg 3 (`psycopg[binary]`);
- normalizes Coolify `postgres://` / `postgresql://` URLs to SQLAlchemy `postgresql+psycopg://`;
- makes Boolean server defaults PostgreSQL-compatible in model metadata and migrations;
- changes the local Docker helper to PostgreSQL 18;
- changes Coolify environment and deployment guidance to PostgreSQL port 5432;
- replaces the SQLite->MySQL helper with a PostgreSQL-only migration helper;
- reseeds PostgreSQL serial/identity sequences after copying explicit SQLite IDs;
- keeps PostgreSQL private on the Coolify internal network;
- retains SQLite only for local/test usage.

Historical project/reference documents may still mention MySQL because they preserve earlier requirements.
For deployment, this release note and `COOLIFY_HOSTINGER_DEPLOYMENT.md` supersede those older references.
