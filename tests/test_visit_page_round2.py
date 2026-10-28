"""DA-led visit reporting and monitoring regressions for v2026.27.27."""
from pathlib import Path

from app.services.reports import report_summary

ROOT = Path(__file__).resolve().parents[1]


def code(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_visit_report_kpis_count_each_village_once():
    rows = [
        {"status": "Recorded", "people_attended": 24, "new_members": 29},
        {"status": "Recorded", "people_attended": 8, "new_members": 2},
    ]
    totals = report_summary(rows)
    assert totals["total"] == 2
    assert totals["Recorded"] == 2
    assert totals["people_attended"] == 32
    assert totals["new_members"] == 31


def test_reports_metrics_no_longer_center_legacy_plan_status():
    template = code("app/templates/reports.html")
    for metric in ("Recorded", "people_attended", "new_members"):
        assert f'data-report-metric="{metric}"' in template
    assert 'data-report-metric="On-time"' not in template
    assert 'data-report-metric="Postponed"' not in template


def test_monitor_map_rejects_missing_and_zero_coordinates():
    script = code("app/static/js/monitoring.js")
    assert 'item.latitude === null' in script
    assert 'item.longitude === null' in script
    assert 'Math.abs(lat) < 0.000001' in script
    assert 'missing = items.filter((item) => !hasCoordinates(item))' in script
    assert 'id="monitor-unmapped"' in code("app/templates/monitoring.html")


def test_current_map_evidence_is_attendance_only():
    service = code("app/services/monitoring.py")
    assert 'return f"/api/v1/photos/attendance/{entry.id}"' in service
    assert "village.specials_entries" not in service
    assert '"Attendance" if latest_evidence else None' in service


def test_analytics_shows_empty_message_if_all_bars_are_zero():
    script = code("app/static/js/visit-analytics.js")
    assert 'items.every((item) => num(item.value) === 0)' in script
    assert 'No attendance recorded for this selection' in script


def test_unmapped_village_list_link_is_available():
    script = code("app/static/js/monitoring.js")
    map_script = code("app/static/js/map.js")
    assert '/map?mode=list' in script
    assert 'get("mode") === "list"' in map_script
    assert 'GPS unavailable' in map_script
