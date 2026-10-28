from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shared_shell_has_no_mojibake_markers():
    source = (ROOT / "app/templates/base.html").read_text(encoding="utf-8")
    suspicious = ("\u00e2", "\u00ef", "\u00c3")
    assert not any(marker in source for marker in suspicious)
    assert "components/reference_ui.html" in source
    assert "icon('menu')" in source
    assert 'aria-label="Open navigation"' in source


def test_desktop_sidebar_uses_single_reference_artwork_footer():
    template = (ROOT / "app/templates/base.html").read_text()
    css = (ROOT / "app/static/css/reference-ui.css").read_text()
    assert template.count('class="ref-sidebar-footer"') == 1
    assert "reference/sidebar-village.png" in template
    assert "Stronger Villages" in template
    assert "rail-account-strip" not in template
    assert "data-rail-toggle" not in template
    assert "--ref-rail:238px" in css
    assert "height:100dvh" in css
    assert "margin:0 0 0 var(--ref-rail)" in css


def test_reference_account_keeps_logout_csrf_and_sync():
    template = (ROOT / "app/templates/base.html").read_text()
    css = (ROOT / "app/static/css/reference-ui.css").read_text()
    assert 'class="ref-account"' in template
    assert 'data-sync-trigger' in template
    assert "url_for('auth.logout')" in template
    assert 'name="csrf_token"' in template
    assert 'id="sync-dialog"' in template
    assert 'id="mobile-menu"' in template
    assert 'data-mobile-menu-open' in template
    assert '@media(max-width:860px)' in css
    assert 'prefers-reduced-motion:reduce' in css
