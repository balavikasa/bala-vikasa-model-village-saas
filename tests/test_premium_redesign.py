"""Critical regression contracts for the official-logo UI renewal and DA-led analytics."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.extensions import db
from app.models import DA, PC, Cluster, Committee, Role, User, Village
from app.timeutils import local_today

ROOT = Path(__file__).resolve().parents[1]


def test_reference_logo_and_pwa_icons_installed():
    with Image.open(ROOT / "app/static/reference/brand-lockup.png") as image:
        assert image.size == (204, 52)
    for name, size in (("icon-192.png", 192), ("icon-512.png", 512), ("icon-maskable-192.png", 192)):
        with Image.open(ROOT / "app/static/icons" / name) as image:
            assert image.size == (size, size)
    base = (ROOT / "app/templates/base.html").read_text()
    assert 'reference/brand-lockup.png' in base
    assert 'reference-ui.css' in base
    assert 'bala-vikasa-official.png' not in base


def test_all_new_analytics_wiring_uses_actual_village_visits():
    analytics = (ROOT / "app/static/js/visit-analytics.js").read_text()
    template = (ROOT / "app/templates/analytics.html").read_text()
    assert "/api/v1/monitoring/visit-analytics" in analytics
    assert "analytics-export" in template
    assert "analytics-month" in template
    assert "analytics-committee" in template
    assert "Scheduled" not in template
    assert "On-time" not in template


def test_live_analytics_scope_and_no_data(client, app):
    with app.app_context():
        pc = PC(full_name="PC A", cluster=Cluster.CSRB)
        da = DA(full_name="DA A", pc=pc)
        village = Village(name="Test Village", da=da)
        committee = Committee(name="Water", village=village, committee_type="Water")
        administrator = User(email="admin-renewal@example.org", display_name="Admin", role=Role.ADMIN)
        administrator.set_password("ExamplePassword123")
        associate = User(email="da-renewal@example.org", display_name="DA", role=Role.DA, da=da)
        associate.set_password("ExamplePassword123")
        db.session.add_all([pc, da, village, committee, administrator, associate])
        db.session.commit()
        village_id, da_id = village.id, da.id
    client.post("/login", data={"identifier": "da-renewal@example.org", "password": "ExamplePassword123"})
    assert client.get("/api/v1/monitoring/visit-analytics").status_code == 403
    client.post("/logout")
    client.post("/login", data={"identifier": "admin-renewal@example.org", "password": "ExamplePassword123"})
    period = local_today().strftime("%Y-%m")
    response = client.get(f"/api/v1/monitoring/visit-analytics?month={period}")
    assert response.status_code == 200
    assert response.json["counts"]["villages"] == 1
    assert response.json["counts"]["villages_done"] == 0
    assert response.json["counts"]["people_attended"] == 0
    assert response.json["filters"]["villages"] == [{"id": village_id, "name": "Test Village"}]
    assert client.get(f"/api/v1/monitoring/visit-analytics?month={period}&da={da_id}").status_code == 200
    assert client.get("/api/v1/monitoring/visit-analytics?month=invalid").status_code == 422
    assert client.get("/api/v1/monitoring/recent").status_code == 200
