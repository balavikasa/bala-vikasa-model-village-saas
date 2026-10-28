from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_monitoring_is_operational_only():
    source = (ROOT / "app" / "templates" / "monitoring.html").read_text(
        encoding="utf-8"
    )

    assert 'id="village-map"' in source
    assert 'id="monitor-status-list"' in source
    assert "pages.analytics" in source
    assert 'src="/dash/"' not in source
    assert "Interactive analytics" not in source
    assert "dash-embed-card" not in source


def test_analytics_page_owns_dash_embed():
    source = (ROOT / "app" / "templates" / "analytics.html").read_text(
        encoding="utf-8"
    )

    assert "Program analytics" in source
    assert 'src="/dash/"' in source
    assert "pages.monitoring" in source


def test_analytics_route_matches_dash_authorization():
    source = (ROOT / "app" / "pages.py").read_text(encoding="utf-8")

    assert '@bp.get("/analytics")' in source
    assert "@role_required(Role.ADMIN, Role.PM, Role.PC)" in source
    assert 'return render_template("analytics.html")' in source


def test_desktop_nav_is_role_aware_and_bounded():
    source = (ROOT / "app" / "templates" / "base.html").read_text(
        encoding="utf-8"
    )
    desktop_nav = source.split('<nav class="rail-nav">', 1)[1].split(
        "</nav>", 1
    )[0]

    assert '<span class="nav-label">Analytics</span>' in desktop_nav
    assert '<span class="nav-label">Monitoring</span>' in desktop_nav
    assert '<span class="nav-label">Master Data</span>' in desktop_nav

    # Recycle Bin stays available elsewhere, but not as a permanent desktop
    # slot. That keeps the Admin rail at eight links.
    assert '<span class="nav-label">Recycle Bin</span>' not in desktop_nav

    # DA remains field-focused; analytics/monitoring are in the non-DA branch.
    da_branch = desktop_nav.split("{% else %}", 1)[0]
    assert "pages.analytics" not in da_branch
    assert "pages.monitoring" not in da_branch


def test_mobile_bottom_nav_remains_unchanged():
    source = (ROOT / "app" / "templates" / "base.html").read_text(
        encoding="utf-8"
    )

    bottom_nav = source.split(
        '<nav class="bottom-nav" aria-label="Mobile navigation">',
        1,
    )[1].split("</nav>", 1)[0]
    assert "pages.analytics" not in bottom_nav

    mobile_menu = source.split(
        '<nav class="mobile-menu-nav" aria-label="All navigation">',
        1,
    )[1].split("</nav>", 1)[0]
    assert "pages.analytics" in mobile_menu


def test_all_desktop_role_navs_fit_without_scrolling_contract():
    css = (ROOT / "app" / "static" / "css" / "app.css").read_text(
        encoding="utf-8"
    )

    assert "Monitoring / Analytics navigation split v2026.27.12" in css
    assert "grid-auto-rows: 44px;" in css
    assert "overflow: visible;" in css
    assert "scrollbar-width: none;" in css
    assert "@media (min-width: 760px) and (max-height: 620px)" in css
