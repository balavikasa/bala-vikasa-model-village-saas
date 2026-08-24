
from __future__ import annotations


def test_login_page_and_security_headers(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Content-Security-Policy" in response.headers
    assert response.headers.get("Referrer-Policy")


def test_manifest_is_served(client):
    response = client.get("/manifest.json")
    if response.status_code == 404:
        response = client.get("/static/manifest.json")
    assert response.status_code == 200
    assert "json" in response.content_type


def test_root_scoped_service_worker_is_served(client):
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert "javascript" in response.content_type
    assert response.headers.get("Service-Worker-Allowed", "/") == "/"


def test_private_api_rejects_anonymous_user(client):
    response = client.get("/api/v1/me")
    assert response.status_code in {302, 401, 403}
