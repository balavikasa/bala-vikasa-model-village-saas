from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mobile_ui_polish_contract():
    css = (ROOT / "app" / "static" / "css" / "app.css").read_text(
        encoding="utf-8"
    )

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


def test_modern_design_tokens_and_motion_contract():
    css = (ROOT / "app" / "static" / "css" / "app.css").read_text(
        encoding="utf-8"
    )

    expected_tokens = {
        "--mv-primary: #0C7C86",
        "--mv-primary-2: #13A0A8",
        "--mv-page: #F4FAFA",
        "--mv-surface: #FFFFFF",
        "--mv-text: #163036",
        "--mv-muted: #6B7F83",
        "--mv-success: #3A9B70",
        "--mv-warning: #F0A53A",
        "--mv-danger: #D95E4F",
    }

    for token in expected_tokens:
        assert token in css

    assert ".mv-enter" in css
    assert ".mv-primary-action" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
def test_da_field_shell_css_contract():
    css = (
        ROOT
        / "app"
        / "static"
        / "css"
        / "app.css"
    ).read_text(encoding="utf-8")

    for selector in (
        ".da-field-appbar",
        ".da-field-brand",
        ".da-sync-button",
        ".da-field-menu-button",
        ".da-field-bottom-nav",
        ".da-field-bottom-nav .is-active",
    ):
        assert selector in css

    assert "min-height: 44px" in css
    assert "backdrop-filter: blur(" in css
