from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_admin_report_mutation_controls_are_role_guarded():
    detail = (ROOT / "app" / "templates" / "report_detail.html").read_text(encoding="utf-8")
    reports = (ROOT / "app" / "static" / "js" / "reports.js").read_text(encoding="utf-8")
    routes = (ROOT / "app" / "reports.py").read_text(encoding="utf-8")

    assert "current_user.role.value == 'admin'" in detail
    assert "data-report-delete-plan" in detail
    assert "Edit plan" in detail
    assert "Recycle Bin" in detail
    assert 'window.MV?.role === "admin"' in reports
    assert '@bp.delete("/api/v1/reports/plan/<int:plan_id>")' in routes
    assert "current_user.role != Role.ADMIN" in routes
    assert "soft_delete(" in routes


def test_mobile_shell_has_direct_logout_and_global_recycle_access():
    source = (ROOT / "app" / "templates" / "base.html").read_text(encoding="utf-8")

    assert "mobile-quick-logout" in source
    assert 'aria-label="Sign out"' in source
    assert '<span class="nav-label">Recycle Bin</span>' in source
    assert "<strong>Recycle Bin</strong>" in source
