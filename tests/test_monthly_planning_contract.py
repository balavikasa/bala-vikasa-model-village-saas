from __future__ import annotations

from pathlib import Path

from app.extensions import db

ROOT = Path(__file__).resolve().parents[1]


def test_monthly_action_plan_columns(app):
    with app.app_context():
        columns = {column.name for column in db.metadata.tables["action_plans"].columns}
        assert {"plan_month", "plan_type", "prepared_from_id", "assigned_date"} <= columns


def test_visit_member_snapshot_contract(app):
    with app.app_context():
        columns = {column.name for column in db.metadata.tables["attendance_visit_members"].columns}
        assert {
            "attendance_entry_id",
            "committee_member_id",
            "member_name_snapshot",
            "designation_snapshot",
            "gender_snapshot",
        } <= columns


def test_specials_are_plan_linked_and_status_aware(app):
    with app.app_context():
        columns = {column.name for column in db.metadata.tables["specials_entries"].columns}
        assert {"action_plan_id", "status", "reason"} <= columns


def test_reports_list_is_view_first():
    template = (ROOT / "app" / "templates" / "reports.html").read_text(encoding="utf-8")
    script = (ROOT / "app" / "static" / "js" / "reports.js").read_text(encoding="utf-8")
    assert "View" in script
    assert "report-detail" not in template.lower() or "View" in script


def test_import_preview_and_prepare_next_month_contracts():
    source = (ROOT / "app" / "services" / "monthly_plans.py").read_text(encoding="utf-8")
    assert "preview_import" in source
    assert "confirm_import" in source
    assert "prepare_next_month" in source
    assert "immutable history" in source.lower()
