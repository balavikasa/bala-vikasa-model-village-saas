from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_report_map_reflows_after_responsive_layout_changes():
    script = (ROOT / "app" / "static" / "js" / "report-detail.js").read_text(encoding="utf-8")
    css = (ROOT / "app" / "static" / "css" / "app.css").read_text(encoding="utf-8")

    assert "ResizeObserver" in script
    assert "invalidateSize" in script
    assert "orientationchange" in script
    assert "requestAnimationFrame" in script
    assert "grid-column: 1 / -1 !important" in css
    assert ".report-map .leaflet-tile" in css
