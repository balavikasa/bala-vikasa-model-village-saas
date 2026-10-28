"""Guardrails for the DA attendance theme without changing submission behavior."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_village_attendance_loads_reference_stylesheet():
    template = (ROOT / "app/templates/village_attendance.html").read_text()
    base = (ROOT / "app/templates/base.html").read_text()
    assert "ref-attendance" in template
    assert "css/reference-ui.css" in base
    for title in ("Select Village", "Committee Attendance", "Visit Summary"):
        assert title in template
    assert 'id="village-attendance-form"' in template
    assert 'id="submit-village-attendance"' in template


def test_attendee_tiles_keep_accessible_selection_and_count_metadata():
    script = (ROOT / "app/static/js/village-attendance.js").read_text()
    assert "aria-pressed" in script
    assert "data-visit-member" in script
    assert "data-gender" in script
    assert "attendee-chip-role" in script
    assert "#village-male" in script
    assert "#village-female" in script
    assert "/api/v1/attendance/village" in script
    assert "window.MVQueue.enqueue" in script


def test_offline_shell_precaches_reference_theme():
    worker = (ROOT / "app/static/sw.js").read_text()
    assert '"/static/css/reference-ui.css?v=2026.27.33"' in worker
    assert '"/static/js/reference-ui.js?v=2026.27.33"' in worker
    assert '"/static/brand/bala-vikasa-symbol.png"' in worker


def test_village_summary_only_shows_committee_count():
    template = (ROOT / "app/templates/village_attendance.html").read_text()
    script = (ROOT / "app/static/js/village-attendance.js").read_text()
    assert 'id="summary-committees"' in template
    assert 'id="summary-pending"' not in template
    assert 'id="summary-submitted"' not in template
    assert "#summary-pending" not in script
    assert "#summary-submitted" not in script
