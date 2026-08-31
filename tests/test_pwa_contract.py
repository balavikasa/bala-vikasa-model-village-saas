
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"


def test_manifest_is_installable():
    manifest = json.loads((STATIC / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["display"] == "standalone"
    assert manifest["start_url"].startswith("/")
    assert manifest["background_color"]
    assert manifest["theme_color"]
    assert manifest.get("orientation") in {"any", "portrait", "portrait-primary"}
    sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert {"192x192", "512x512"} <= sizes
    assert any("maskable" in icon.get("purpose", "") for icon in manifest["icons"])

def test_service_worker_refreshes_static_assets_from_network():
    source = (STATIC / "sw.js").read_text(encoding="utf-8")

    assert "networkFirstStatic" in source
    assert 'url.pathname.startsWith("/static/")' in source
    assert "event.respondWith(networkFirstStatic(request))" in source


def test_service_worker_has_offline_and_sync_contracts():
    source = (STATIC / "sw.js").read_text(encoding="utf-8")
    assert "caches.open" in source
    assert "indexedDB" in source or "MVQueue" in source
    assert "sync" in source
    assert "fetch" in source
    assert "Cache" in source or "cache" in source
    assert "Network" in source or "network" in source


def test_field_client_compresses_to_webp_and_uses_geolocation():
    source = (STATIC / "js" / "field.js").read_text(encoding="utf-8")
    assert "image/webp" in source
    assert "toBlob" in source
    assert "geolocation" in source
    assert "client_submission_id" in source or "clientId" in source or "submissionId" in source


def test_touch_target_and_adaptive_breakpoints_exist():
    css = (STATIC / "css" / "app.css").read_text(encoding="utf-8")
    compact = "".join(css.split())
    assert "44px" in compact
    assert "@media" in css
    assert "min-width" in css or "max-width" in css
def test_generated_pwa_icon_set_dimensions():
    from PIL import Image

    expected = {
        "icon-192.png": (192, 192),
        "icon-512.png": (512, 512),
        "icon-maskable-192.png": (192, 192),
        "icon-maskable-512.png": (512, 512),
        "apple-touch-icon.png": (180, 180),
        "favicon-32.png": (32, 32),
    }

    for name, size in expected.items():
        with Image.open(STATIC / "icons" / name) as image:
            assert image.size == size
