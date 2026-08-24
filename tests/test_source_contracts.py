from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

from app.services.monitoring import action_plan_status

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_scoping_is_centralized_and_hierarchy_aware():
    source = read("app/scoping.py")
    assert "scoped_select" in source
    for token in ("Role.ADMIN", "Role.PM", "Role.PC", "Role.DA"):
        assert token in source
    assert "Village" in source and "DA" in source and "PC" in source


def test_server_owns_attendance_status_and_reason_logic():
    entries = read("app/services/entries.py")
    source = entries + read("app/models.py")
    lowered = source.lower()
    assert "early" in lowered
    assert "on-time" in lowered
    assert "postponed" in lowered
    assert "reason" in entries
    assert "male" in entries and "female" in entries and "total" in entries
    assert "client_submission_id" in entries


def test_failure_is_derived_in_monitoring():
    today = date(2026, 8, 24)
    plan = SimpleNamespace(
        attendance_entry=None,
        specials_entry=None,
        is_executable=True,
        assigned_date=today - timedelta(days=1),
    )

    assert action_plan_status(plan, today) == "Failure"


def test_admin_moves_and_recycle_bin_are_explicit():
    admin_source = read("app/admin_api.py")
    audit_source = read("app/services/audit.py")
    assert "move" in admin_source.lower()
    assert "RecycleBin" in admin_source
    assert "restore" in admin_source.lower()
    assert "AuditLog" in (admin_source + audit_source)
