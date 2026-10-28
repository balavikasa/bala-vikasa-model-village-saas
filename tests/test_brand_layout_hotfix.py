"""Backend contracts accompanying the isolated Chromium v32 regression suite."""
from __future__ import annotations


def test_exact_tile_host_is_allowed_without_weakening_script_policy(client):
    policy = client.get('/login').headers['Content-Security-Policy']
    directives = dict(part.strip().split(' ', 1) for part in policy.split(';') if part.strip())
    assert 'https://tile.openstreetmap.org' in directives['img-src'].split()
    assert 'https://tile.openstreetmap.org' in directives['connect-src'].split()
    assert "'unsafe-inline'" not in directives['script-src']
    assert '*' not in directives['img-src'].split()


def test_login_brand_uses_original_emblem_without_year(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'brand/bala-vikasa-symbol.png' in response.data
    assert b'Bala Vikasa emblem' in response.data
    assert b'Model Village 2026-27' not in response.data
    assert b'icons/favicon-32.png?v=2026.27.32' in response.data
