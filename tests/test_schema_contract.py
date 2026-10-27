
from __future__ import annotations

from app.extensions import db

EXPECTED_TABLES = {
    "pms",
    "pcs",
    "das",
    "villages",
    "committees",
    "committee_members",
    "action_plans",
    "attendance_visit_members",
    "village_attendance_visits",
    "attendance_entries",
    "specials_entries",
    "users",
    "audit_logs",
    "recycle_bin",
}


def columns(table_name: str) -> set[str]:
    return {column.name for column in db.metadata.tables[table_name].columns}


def test_explicit_fourteen_table_contract(app):
    with app.app_context():
        assert set(db.metadata.tables) == EXPECTED_TABLES


def test_cluster_is_persisted_only_on_pc(app):
    with app.app_context():
        assert "cluster" in columns("pcs")
        assert "cluster" not in columns("das")
        assert "cluster" not in columns("villages")


def test_lifecycle_fields_are_consistent(app):
    with app.app_context():
        lifecycle = {"is_enabled", "is_deleted", "deleted_at"}
        normal_tables = EXPECTED_TABLES - {"audit_logs", "recycle_bin"}
        for table_name in normal_tables:
            assert lifecycle <= columns(table_name), table_name


def test_offline_idempotency_keys_are_unique(app):
    with app.app_context():
        for table_name in ("attendance_entries", "specials_entries"):
            table = db.metadata.tables[table_name]
            assert "client_submission_id" in columns(table_name)
            unique_columns = {
                column.name
                for column in table.columns
                if column.unique
            }
            unique_constraints = {
                column.name
                for constraint in table.constraints
                if getattr(constraint, "columns", None)
                for column in constraint.columns
                if constraint.__class__.__name__ == "UniqueConstraint"
            }
            assert "client_submission_id" in unique_columns | unique_constraints


def test_attendance_counts_are_normalized(app):
    with app.app_context():
        attendance = columns("attendance_entries")
        assert {"male_count", "female_count", "total_count"} <= attendance


def test_one_village_visit_can_hold_many_committee_attendance_rows(app):
    with app.app_context():
        visits = db.metadata.tables["village_attendance_visits"]
        attendance = db.metadata.tables["attendance_entries"]
        assert {"village_id", "visit_date", "photo_path", "latitude", "longitude",
                "client_submission_id"} <= columns("village_attendance_visits")
        visit_id = attendance.c.village_visit_id
        assert visit_id.nullable  # Old per-committee submissions remain readable.
        assert any(
            foreign_key.column.table is visits for foreign_key in visit_id.foreign_keys
        )
