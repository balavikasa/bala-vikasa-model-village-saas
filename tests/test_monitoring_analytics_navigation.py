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


def test_analytics_page_uses_live_visit_series_without_nested_dash_frame():
    source = (ROOT / "app/templates/analytics.html").read_text()
    assert "Model Village Analytics" in source
    assert 'src="/dash/"' not in source
    for name in ("analytics-completion", "analytics-gender", "analytics-trend", "analytics-export"):
        assert 'id="' + name + '"' in source
    assert "pages.map_page" in source


def test_analytics_route_matches_dash_authorization():
    source = (ROOT / "app" / "pages.py").read_text(encoding="utf-8")

    assert '@bp.get("/analytics")' in source
    assert "@role_required(Role.ADMIN, Role.PM, Role.PC)" in source
    assert 'return render_template("analytics.html")' in source


def test_desktop_nav_is_role_aware_and_bounded():
    source = (ROOT / "app/templates/base.html").read_text()
    nav = source.split("{% set nav =", 1)[1].split("%}", 1)[0]
    da, management = nav.split("if da else", 1)
    assert "pages.analytics" not in da
    assert "pages.monitoring" not in da
    assert "pages.analytics" in management
    assert "pages.monitoring" in management
    desktop = source.split('<nav class="ref-nav">', 1)[1].split('</nav>', 1)[0]
    assert "Administration" in desktop
    assert "Recycle Bin" not in desktop


def test_mobile_bottom_nav_is_field_focused_with_complete_more_menu():
    source = (ROOT / "app/templates/base.html").read_text()
    bottom = source.split('<nav class="ref-bottom-nav', 1)[1].split('</nav>', 1)[0]
    assert "pages.analytics" not in bottom
    assert "pages.attendance" in bottom
    assert "data-mobile-menu-open" in bottom
    menu = source.split('<dialog id="mobile-menu"', 1)[1].split('</dialog>', 1)[0]
    assert "for label,glyph,href,key in nav" in menu
    assert "data-mobile-menu-close" in menu


def test_reference_sidebar_reserves_content_space_and_allows_short_screen_scrolling():
    css = (ROOT / "app/static/css/reference-ui.css").read_text()
    assert "--ref-rail:238px" in css
    assert "width:calc(100% - var(--ref-rail))" in css
    assert "height:100dvh" in css
    assert "overflow-y:auto" in css
    assert "@media(max-width:860px)" in css
