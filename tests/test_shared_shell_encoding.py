from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_shared_shell_has_no_mojibake_markers():
    source = (ROOT / "app" / "templates" / "base.html").read_text(encoding="utf-8")

    # Common first characters produced when UTF-8 icon bytes are decoded as
    # Windows-1252 and then written back as UTF-8.
    suspicious = ("\u00e2", "\u00ef", "\u00c3")

    assert not any(marker in source for marker in suspicious)
    assert "&#9776;" in source
    assert "&#10003;" in source
def test_desktop_sidebar_uses_single_bmw_footer():
    template = (ROOT / "app" / "templates" / "base.html").read_text(
        encoding="utf-8"
    )
    css = (ROOT / "app" / "static" / "css" / "app.css").read_text(
        encoding="utf-8"
    )
    javascript = (ROOT / "app" / "static" / "js" / "app.js").read_text(
        encoding="utf-8"
    )

    assert 'class="rail-account-strip"' in template
    assert 'class="rail-account-name"' in template
    assert 'class="rail-status-button"' in template
    assert 'class="rail-account-logout"' in template

    assert 'data-rail-toggle' not in template
    assert 'class="sync-card"' not in template
    assert 'class="user-card"' not in template
    assert 'class="rail-signout"' not in template

    assert "BMW M-inspired desktop sidebar footer" in css
    assert "#0066B1" in css
    assert "#003C78" in css
    assert "#E22718" in css
    assert "scrollbar-width: none;" in css
    assert ".rail-nav::-webkit-scrollbar" in css

    assert 'localStorage.removeItem("mv-rail-collapsed")' in javascript
    assert 'document.body.classList.remove("rail-collapsed")' in javascript
def test_desktop_sidebar_footer_contract():
    template = (ROOT / "app" / "templates" / "base.html").read_text(
        encoding="utf-8"
    )
    css = (ROOT / "app" / "static" / "css" / "app.css").read_text(
        encoding="utf-8"
    )
    javascript = (ROOT / "app" / "static" / "js" / "app.js").read_text(
        encoding="utf-8"
    )

    assert 'class="rail-account-strip"' in template
    assert 'class="rail-account-name"' in template
    assert 'class="rail-status-button"' in template
    assert 'class="rail-account-logout"' in template
    assert "data-rail-toggle" not in template

    assert "BMW-inspired desktop navigation polish" in css
    assert "Desktop title scale and mobile color-only polish" in css
    assert "scrollbar-width: none;" in css
    assert ".rail-nav::-webkit-scrollbar" in css
    assert "@media (min-width: 1080px)" in css
    assert "@media (max-width: 759px)" in css

    assert 'localStorage.removeItem("mv-rail-collapsed")' in javascript
    assert 'document.body.classList.remove("rail-collapsed")' in javascript
