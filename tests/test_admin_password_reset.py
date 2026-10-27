"""DA/PC login password reset through System Administration."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func

from app.extensions import db
from app.models import DA, PC, AuditAction, AuditLog, Cluster, Role, User, utcnow


def _create_staff(app):
    with app.app_context():
        pc = PC(full_name="Reset PC", cluster=Cluster.PDTC)
        da = DA(full_name="Reset DA", pc=pc)
        no_login_pc = PC(full_name="Unlinked PC", cluster=Cluster.CSRB)
        admin = User(email="reset-admin@example.org", display_name="Admin", role=Role.ADMIN)
        pc_user = User(
            display_name="PC Login", mobile="9876543210", role=Role.PC, pc=pc
        )
        da_user = User(
            display_name="DA Login", mobile="9876543211", role=Role.DA, da=da
        )
        for user in (admin, pc_user, da_user):
            user.set_password("OriginalPassword123")
        db.session.add_all([pc, da, no_login_pc, admin, pc_user, da_user])
        db.session.commit()
        return admin.id, pc.id, da.id, pc_user.id, da_user.id, no_login_pc.id


def _admin_login(client):
    response = client.post(
        "/login",
        data={"identifier": "reset-admin@example.org", "password": "OriginalPassword123"},
    )
    assert response.status_code in {302, 303}


def _reset(client, path, password="DifferentPassword456", confirm=None):
    return client.post(
        path,
        json={"password": password, "confirm_password": password if confirm is None else confirm},
    )


def test_password_reset_from_pc_da_and_users_succeeds_and_is_audited(client, app):
    _, pc_id, da_id, pc_user_id, da_user_id, _ = _create_staff(app)
    _admin_login(client)

    pc_response = _reset(client, f"/api/v1/admin/pcs/{pc_id}/reset-password")
    assert pc_response.status_code == 200
    assert pc_response.json["account_enabled"] is True
    da_response = _reset(client, f"/api/v1/admin/das/{da_id}/reset-password")
    assert da_response.status_code == 200
    user_response = _reset(
        client, f"/api/v1/admin/users/{da_user_id}/reset-password", "ThirdPassword789"
    )
    assert user_response.status_code == 200

    with app.app_context():
        pc_user = db.session.get(User, pc_user_id)
        da_user = db.session.get(User, da_user_id)
        assert pc_user.check_password("DifferentPassword456")
        assert da_user.check_password("ThirdPassword789")
        assert not pc_user.check_password("OriginalPassword123")
        assert not da_user.check_password("OriginalPassword123")
        assert pc_user.password_changed_at is not None
        resets = db.session.scalars(
            db.select(AuditLog)
            .where(AuditLog.action == AuditAction.UPDATE, AuditLog.entity_type == "User")
            .order_by(AuditLog.id)
        ).all()
        assert len(resets) == 3
        assert all(event.after_json["password_reset"] is True for event in resets)
        assert all("password_hash" not in str(event.before_json) for event in resets)
        assert all("password_hash" not in str(event.after_json) for event in resets)
        assert "ThirdPassword789" not in str(resets)

    client.post("/logout")
    assert client.post(
        "/login", data={"identifier": "9876543210", "password": "OriginalPassword123"}
    ).status_code == 200
    assert client.post(
        "/login", data={"identifier": "9876543210", "password": "DifferentPassword456"}
    ).status_code in {302, 303}


def test_reset_validations_and_missing_account_leave_password_unchanged(client, app):
    _, pc_id, da_id, pc_user_id, da_user_id, no_login_id = _create_staff(app)
    _admin_login(client)
    path = f"/api/v1/admin/pcs/{pc_id}/reset-password"
    assert _reset(client, path, "short").status_code == 422
    assert _reset(client, path, "DifferentPassword456", "Mismatch123456").status_code == 422
    assert _reset(client, path, "OriginalPassword123").status_code == 422
    assert _reset(client, f"/api/v1/admin/pcs/{no_login_id}/reset-password").status_code == 409
    assert _reset(client, f"/api/v1/admin/das/{da_id + 500}/reset-password").status_code == 404
    assert _reset(client, f"/api/v1/admin/pms/{pc_id}/reset-password").status_code == 404
    with app.app_context():
        assert db.session.get(User, pc_user_id).check_password("OriginalPassword123")
        assert db.session.get(User, da_user_id).check_password("OriginalPassword123")
        assert db.session.scalar(db.select(func.count(AuditLog.id)).where(
            AuditLog.action == AuditAction.UPDATE
        )) == 0


def test_non_admin_cannot_reset_and_locked_user_is_unlocked(client, app):
    _, pc_id, _, pc_user_id, da_user_id, _ = _create_staff(app)
    path = f"/api/v1/admin/pcs/{pc_id}/reset-password"
    assert _reset(client, path).status_code == 401
    assert client.post(
        "/login", data={"identifier": "9876543211", "password": "OriginalPassword123"}
    ).status_code in {302, 303}
    assert _reset(client, path).status_code == 403
    client.post("/logout")
    with app.app_context():
        pc_user = db.session.get(User, pc_user_id)
        pc_user.failed_login_count = 5
        pc_user.locked_until = utcnow() + timedelta(minutes=15)
        db.session.commit()
    _admin_login(client)
    assert _reset(client, path).status_code == 200
    with app.app_context():
        pc_user = db.session.get(User, pc_user_id)
        assert pc_user.failed_login_count == 0
        assert pc_user.locked_until is None
        assert db.session.get(User, da_user_id).check_password("OriginalPassword123")


def test_resources_expose_linked_login_state_only_to_admin(client, app):
    _, pc_id, da_id, pc_user_id, da_user_id, _ = _create_staff(app)
    assert client.get("/api/v1/admin/pcs").status_code == 401
    _admin_login(client)
    pcs = client.get("/api/v1/admin/pcs").json["items"]
    das = client.get("/api/v1/admin/das").json["items"]
    assert next(item for item in pcs if item["id"] == pc_id)["login_user_id"] == pc_user_id
    assert next(item for item in das if item["id"] == da_id)["login_user_id"] == da_user_id
    assert all("password_hash" not in item for item in pcs + das)
