from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_mobile_ui_polish_contract():
    css = (ROOT / "app" / "static" / "css" / "app.css").read_text(encoding="utf-8")

    assert "Mobile UI/UX polish v2026.27.8" in css
    assert "@media (max-width: 619px)" in css
    assert "font-size: 16px;" in css
    assert ".split-heading" in css
    assert ".panel-card" in css
    assert ".field-layout" in css
    assert ".report-bento" in css
    assert ".detail-list > div" in css
    assert ".hero-overview" in css
    assert ".admin-card" in css
    assert ".mobile-menu-sheet" in css
    assert ".bottom-nav" in css

