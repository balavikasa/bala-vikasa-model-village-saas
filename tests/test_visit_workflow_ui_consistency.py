"""Smoke contracts for the DA-led page repair and actual-visit reporting."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_analytics_renders_live_api_visuals_without_embedded_dash():
    template = read("app/templates/analytics.html")
    script = read("app/static/js/visit-analytics.js")
    assert "analytics-completion" in template
    assert "/dash/" not in template
    assert "/api/v1/monitoring/visit-analytics" in script
    assert "No attendance in this selection." in script


def test_detailed_village_report_keeps_responsive_metadata_columns():
    template = read("app/templates/village_attendance_report.html")
    css = read("app/static/css/reference-ui.css")
    for name in ("ref-report-kpis", "ref-report-photo", "ref-report-ledger", "ref-report-bottom"):
        assert name in template
        assert "." + name in css
    assert 'data-single-map' in template
    assert 'Village-level Remarks' in template
    assert 'minmax(0,1fr)' in css
    assert '@media(max-width:860px)' in css


def test_village_profile_shows_visits_and_attendance_not_draft_plan_columns():
    profile = read("app/templates/profile.html")
    service = read("app/services/profiles.py")
    assert "Attended this month" in profile
    assert "Last visit" in profile
    assert "On-plan pulse" not in profile
    assert '_village_visit_summary' in service
    assert '"Visited" if current_attendance else "Not visited"' in service


def test_navigation_is_da_led_and_historical_plans_remain_accessible():
    base = read("app/templates/base.html")
    overview = read("app/templates/overview.html")
    nav = base.split("{% set nav =", 1)[1].split("%}", 1)[0]
    assert "Past plans" not in nav
    assert "Action Plans" not in nav
    assert "My Villages" in nav
    assert "planning.action_plans_page" in overview


def test_new_da_village_visit_does_not_link_to_a_nonexistent_action_plan_editor():
    script = read("app/static/js/reports.js")
    service = read("app/services/reports.py")
    assert 'row.plan_id ?' in script
    assert '"status": "Recorded"' in service
