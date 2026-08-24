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
