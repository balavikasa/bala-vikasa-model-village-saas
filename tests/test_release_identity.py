from __future__ import annotations

from pathlib import Path


def test_public_health_check_exposes_release_for_deployment_verification(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json == {"status": "ok", "release": "2026.27.28"}
    assert response.headers["X-MV-Release"] == "2026.27.28"


def test_pwa_cache_version_matches_release():
    sw = (Path(__file__).resolve().parents[1] / "app/static/sw.js").read_text()
    assert 'const VERSION = "2026.27.28-visit-report-export"' in sw
