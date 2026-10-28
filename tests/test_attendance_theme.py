"""Guardrails for the DA attendance theme without changing submission behavior."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_village_attendance_loads_scoped_stylesheet():
    template = (ROOT / "app/templates/village_attendance.html").read_text()
    assert "attendance-fresh-theme" in template
    assert "css/attendance-theme.css" in template
    assert "Your village visit" in template
    assert "Tap who attended" in template
    assert "Finish village visit" in template
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


def test_offline_shell_precaches_new_theme():
    worker = (ROOT / "app/static/sw.js").read_text()
    assert 'const VERSION = "2026.27.24-attendance-theme"' in worker
    assert '"/static/css/attendance-theme.css"' in worker
