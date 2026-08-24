from __future__ import annotations


def test_liveness(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_readiness_checks_database(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
