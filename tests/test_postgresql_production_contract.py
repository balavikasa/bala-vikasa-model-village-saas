from __future__ import annotations

from pathlib import Path

from app import config

ROOT = Path(__file__).resolve().parents[1]


def test_coolify_postgres_url_uses_psycopg3(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgres://model_village:secret@postgres:5432/model_village",
    )
    assert config._database_url() == (
        "postgresql+psycopg://model_village:secret@postgres:5432/model_village"
    )


def test_standard_postgresql_url_uses_psycopg3(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://model_village:secret@postgres:5432/model_village",
    )
    assert config._database_url() == (
        "postgresql+psycopg://model_village:secret@postgres:5432/model_village"
    )


def test_production_release_has_postgresql_driver_and_no_pymysql():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "psycopg[binary]" in requirements
    assert "PyMySQL" not in requirements


def test_initial_boolean_defaults_are_postgresql_safe():
    first = (
        ROOT / "migrations" / "versions" / "20260821_0001_initial_schema.py"
    ).read_text(encoding="utf-8")
    second = (
        ROOT / "migrations" / "versions" / "20260822_0002_monthly_planning_reports.py"
    ).read_text(encoding="utf-8")

    assert 'server_default=sa.text("true")' in first
    assert 'server_default=sa.text("false")' in first
    assert 'server_default=sa.text("true")' in second
    assert 'server_default=sa.text("false")' in second


def test_integer_defaults_remain_numeric():
    models = (ROOT / "app" / "models.py").read_text(encoding="utf-8")
    second = (
        ROOT / "migrations" / "versions" / "20260822_0002_monthly_planning_reports.py"
    ).read_text(encoding="utf-8")

    assert 'failed_login_count: Mapped[int]' in models
    assert 'failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")' in models
    assert 'new_members_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")' in models
    assert 'sa.Column("new_members_count", sa.Integer(), nullable=False, server_default=sa.text("0"))' in second


def test_sqlite_to_postgresql_helper_reseeds_sequences():
    source = (
        ROOT / "scripts" / "migrate_sqlite_to_postgresql.py"
    ).read_text(encoding="utf-8")

    assert 'target_engine.dialect.name != "postgresql"' in source
    assert "pg_get_serial_sequence" in source
    assert "setval" in source
    assert "deferred_action_plan_links" in source
