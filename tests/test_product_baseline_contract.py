from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_visit_designation_member_picker_matches_locked_behavior():
    field = read("app/static/js/field.js")
    assert "matches.length === 1" in field
    assert "matches.length > 1" in field
    assert "openMemberPicker" in field
    assert "No name in master" in field


def test_reports_keep_detail_behind_view_action():
    reports = read("app/static/js/reports.js")
    detail = read("app/templates/report_detail.html")
    assert ">View<" in reports or "View" in reports
    assert "Committee Member" in detail
    assert "report-map" in detail
    assert "photo" in detail.lower()


def test_action_plan_transfer_has_preview_confirm_and_prepare_next_month():
    planning = read("app/services/monthly_plans.py")
    client = read("app/static/js/action-plan-transfer.js")
    action_page = read("app/templates/action_plans.html")
    assert "preview_import" in planning
    assert "confirm_import" in planning
    assert "prepare_next_month" in planning
    assert "Validate" in client or "preview" in client.lower()
    assert "Prepare next month" in action_page


def test_mobile_role_navigation_is_explicit():
    base = read("app/templates/base.html")
    for label in ("Home", "Plans", "Reports", "Map"):
        assert f"<small>{label}</small>" in base
    assert "<small>Entry</small>" in base
    assert "<small>Team</small>" in base
    assert "<small>People</small>" in base


def test_admin_master_transfer_is_preview_first_and_non_destructive():
    service = read("app/services/master_transfer.py")
    template = read("app/templates/admin_transfer.html")
    assert "preview_import" in service
    assert "confirm_import" in service
    assert "omission never deletes" in template.lower()
    assert "Moved" in template
