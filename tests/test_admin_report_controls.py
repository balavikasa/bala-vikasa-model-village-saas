from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_admin_report_mutation_controls_are_role_guarded():
    detail = (ROOT / "app" / "templates" / "report_detail.html").read_text(
        encoding="utf-8"
    )
    reports = (ROOT / "app" / "static" / "js" / "reports.js").read_text(
        encoding="utf-8"
    )
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
    source = (ROOT / "app" / "templates" / "base.html").read_text(
        encoding="utf-8"
    )

    assert "mobile-quick-logout" in source
    assert 'aria-label="Sign out"' in source

    mobile_menu = source.split(
        '<nav class="mobile-menu-nav" aria-label="All navigation">',
        1,
    )[1].split("</nav>", 1)[0]

    assert "url_for('pages.admin', tab='recycle')" in mobile_menu
    assert "<strong>Recycle Bin</strong>" in mobile_menu

    desktop_nav = source.split(
        '<nav class="rail-nav">',
        1,
    )[1].split("</nav>", 1)[0]

    # Recycle Bin remains available globally through the Admin/Master Data
    # experience and mobile all-navigation menu, but intentionally does not
    # consume a permanent desktop rail slot.
    assert '<span class="nav-label">Recycle Bin</span>' not in desktop_nav