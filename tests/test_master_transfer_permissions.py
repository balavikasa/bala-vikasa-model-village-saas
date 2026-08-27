from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.models import Role
from app.services.master_transfer import resource_catalog

ROOT = Path(__file__).resolve().parents[1]


def test_admin_catalog_contains_all_master_resources():
    user = SimpleNamespace(role=Role.ADMIN)
    keys = {item["key"] for item in resource_catalog(user)}

    assert keys == {
        "pms",
        "pcs",
        "das",
        "villages",
        "committees",
        "committee-members",
    }


def test_pc_catalog_is_limited_to_its_manageable_hierarchy():
    user = SimpleNamespace(role=Role.PC)
    keys = {item["key"] for item in resource_catalog(user)}

    assert keys == {"das", "villages", "committees", "committee-members"}


def test_transfer_routes_allow_admin_and_pc():
    source = (ROOT / "app" / "admin_transfer.py").read_text(encoding="utf-8")

    assert source.count("@role_required(Role.ADMIN, Role.PC)") == 2
    assert source.count("@json_role_required(Role.ADMIN, Role.PC)") == 2


def test_pc_master_data_navigation_points_to_transfer_page():
    source = (ROOT / "app" / "templates" / "base.html").read_text(encoding="utf-8")

    assert "current_user.role.value in ['admin', 'pc']" in source
    assert "url_for('admin_transfer.page')" in source
