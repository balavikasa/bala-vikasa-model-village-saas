"""Integration checks for the reference UI. Run with the normal Flask test suite."""
from __future__ import annotations

from app.extensions import db
from app.models import DA, PC, Cluster, Role, User, Village


def _accounts(app):
    with app.app_context():
        pc = PC(full_name="Reference PC", cluster=Cluster.CSRB)
        da = DA(full_name="Reference DA", pc=pc)
        other = DA(full_name="Other DA", pc=pc)
        users = [
            User(email="ref-admin@example.test", display_name="Ref Admin", role=Role.ADMIN),
            User(email="ref-da@example.test", display_name="Ref DA", role=Role.DA, da=da),
            User(email="ref-pc@example.test", display_name="Ref PC", role=Role.PC, pc=pc),
            User(email="ref-disabled@example.test", display_name="Disabled", role=Role.DA,
                 da=other, is_enabled=False),
        ]
        for user in users:
            user.set_password("ReferenceTestPassword123")
        db.session.add_all([
            pc, da, other, *users,
            Village(name="Assigned village", da=da),
            Village(name="Other assigned village", da=other),
        ])
        db.session.commit()


def _login(client, role):
    result = client.post("/login", data={
        "identifier": f"ref-{role}@example.test", "password": "ReferenceTestPassword123",
    })
    assert result.status_code == 302


def test_da_default_is_attendance_and_dashboard_is_optional(client, app):
    _accounts(app)
    _login(client, "da")
    assert client.get("/").location.endswith("/field/attendance")
    assert client.get("/overview").location.endswith("/field/attendance")
    assert client.get("/field/attendance").status_code == 200
    assert client.get("/dashboard").status_code == 200
    assert client.get("/admin").status_code == 403


def test_dashboard_series_remains_da_scoped(client, app):
    _accounts(app)
    _login(client, "da")
    response = client.get("/api/v1/dashboard/series")
    assert response.status_code == 200
    assert response.json["counts"]["villages"] == 1
    assert len(response.json["daily_trend"]) == 7
    assert client.get("/api/v1/admin/users").status_code == 403


def test_admin_role_and_enabled_filters(client, app):
    _accounts(app)
    _login(client, "admin")
    result = client.get("/api/v1/admin/users?role=da&enabled=false")
    assert result.status_code == 200
    assert result.json["total"] == 1
    assert result.json["items"][0]["display_name"] == "Disabled"
    assert client.get("/api/v1/admin/users?role=unknown").status_code == 422


def test_new_shell_uses_reference_assets_and_not_prior_logo(client, app):
    _accounts(app)
    _login(client, "admin")
    for path in ("/overview", "/analytics", "/admin", "/directory", "/reports", "/map"):
        response = client.get(path)
        assert response.status_code == 200
        assert b"reference-ui.css" in response.data
        assert b"reference/brand-lockup.png" in response.data
        assert b"bala-vikasa-official.png" not in response.data


def test_report_village_filter_does_not_accept_invalid_identifiers(client, app):
    _accounts(app)
    _login(client, "admin")
    assert client.get("/api/v1/reports?village=invalid").status_code == 422
    assert client.get("/reports/export.xlsx?village=-1").status_code == 422
    assert client.get("/api/v1/reports?village=99999").json["items"] == []


def test_unauthenticated_dashboard_data_is_not_public(client):
    assert client.get("/api/v1/dashboard/series").status_code in {302, 401}
