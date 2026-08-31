from __future__ import annotations

from app.extensions import db
from app.models import DA, PC, Cluster, Role, User


def _create_da_user(app) -> None:
    with app.app_context():
        pc = PC(
            full_name="Test PC",
            cluster=Cluster.CSRB,
        )

        da = DA(
            full_name="Test DA",
            pc=pc,
        )

        user = User(
            email="da-work-hub@example.org",
            role=Role.DA,
            display_name="Test DA",
            da=da,
        )
        user.set_password("1234")

        db.session.add_all([pc, da, user])
        db.session.commit()


def test_da_home_redirects_to_action_plan_work_hub(client, app):
    _create_da_user(app)

    response = client.post(
        "/login",
        data={
            "identifier": "da-work-hub@example.org",
            "password": "1234",
        },
        follow_redirects=False,
    )

    assert response.status_code in {302, 303}

    response = client.get("/", follow_redirects=False)

    assert response.status_code in {302, 303}
    assert response.headers["Location"].endswith("/action-plans")


def test_da_overview_redirects_to_action_plan_work_hub(client, app):
    _create_da_user(app)

    client.post(
        "/login",
        data={
            "identifier": "da-work-hub@example.org",
            "password": "1234",
        },
        follow_redirects=False,
    )

    response = client.get("/overview", follow_redirects=False)

    assert response.status_code in {302, 303}
    assert response.headers["Location"].endswith("/action-plans")


def test_da_action_plans_page_renders_work_hub(client, app):
    _create_da_user(app)

    client.post(
        "/login",
        data={
            "identifier": "da-work-hub@example.org",
            "password": "1234",
        },
        follow_redirects=False,
    )

    response = client.get(
        "/action-plans?month=2026-08",
        follow_redirects=False,
    )

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert 'data-da-work-hub="1"' in html
    assert 'role="tablist"' in html
    assert 'data-work-tab="today"' in html
    assert 'data-work-tab="pending"' in html
    assert 'data-work-panel="today"' in html
    assert 'data-work-panel="pending"' in html
    assert "data-upcoming-work" in html

    assert "Today" in html
    assert "Pending" in html
    assert "Upcoming" in html


def test_da_action_plans_page_hides_management_workspace(client, app):
    _create_da_user(app)

    client.post(
        "/login",
        data={
            "identifier": "da-work-hub@example.org",
            "password": "1234",
        },
        follow_redirects=False,
    )

    response = client.get("/action-plans")

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert 'id="prepare-next-month"' not in html
    assert 'id="plan-search"' not in html
    assert 'id="plan-status-filter"' not in html
    assert 'id="planning-metrics"' not in html


def test_admin_action_plans_page_keeps_management_workspace(client, app):
    with app.app_context():
        admin = User(
            email="work-hub-admin@example.org",
            role=Role.ADMIN,
            display_name="Work Hub Admin",
        )
        admin.set_password("StrongPass123!")

        db.session.add(admin)
        db.session.commit()

    client.post(
        "/login",
        data={
            "identifier": "work-hub-admin@example.org",
            "password": "StrongPass123!",
        },
        follow_redirects=False,
    )

    response = client.get("/action-plans")

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert 'data-da-work-hub="1"' not in html
    assert 'id="planning-metrics"' in html
    assert 'id="plan-search"' in html
    assert 'id="plan-status-filter"' in html
    assert 'id="prepare-next-month"' in html






def test_da_work_queue_api_is_da_only(client, app):
    _create_da_user(app)

    client.post(
        "/login",
        data={
            "identifier": "da-work-hub@example.org",
            "password": "1234",
        },
        follow_redirects=False,
    )

    response = client.get("/api/v1/planning/da-work")

    assert response.status_code == 200

    payload = response.get_json()

    assert set(payload) >= {
        "today",
        "pending",
        "upcoming",
        "counts",
    }


def test_admin_cannot_use_da_work_queue_api(client, app):
    with app.app_context():
        admin = User(
            email="da-work-api-admin@example.org",
            role=Role.ADMIN,
            display_name="API Admin",
        )
        admin.set_password("StrongPass123!")

        db.session.add(admin)
        db.session.commit()

    client.post(
        "/login",
        data={
            "identifier": "da-work-api-admin@example.org",
            "password": "StrongPass123!",
        },
        follow_redirects=False,
    )

    response = client.get("/api/v1/planning/da-work")

    assert response.status_code == 403

def test_da_work_hub_javascript_contract():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]

    source = (
        root
        / "app"
        / "static"
        / "js"
        / "action-plans.js"
    ).read_text(encoding="utf-8")

    assert 'root.dataset.daWorkHub === "1"' in source
    assert '"/api/v1/planning/da-work"' in source

    assert '[data-today-work]' in source
    assert '[data-pending-work]' in source
    assert '[data-upcoming-list]' in source

    assert 'data-work-tab="today"' in source
    assert 'data-work-tab="pending"' in source

    assert "item.go_url" in source
    assert ">GO<" in source

    # Mobile users must be able to both tap tabs and swipe.
    assert '"touchstart"' in source
    assert '"touchend"' in source

    # The DA branch must exit before the management workspace
    # attempts to use its month picker/table controls.
    assert "if (isDaWorkHub)" in source
    assert "initDaWorkHub();" in source

def test_field_javascript_supports_plan_deep_link():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]

    source = (
        root
        / "app"
        / "static"
        / "js"
        / "field.js"
    ).read_text(encoding="utf-8")

    assert 'new URLSearchParams(window.location.search)' in source
    assert 'searchParams.get("plan")' in source
    assert "prefillPlanId" in source

    assert "loadVillages" in source
    assert "loadCommittees" in source
    assert "loadPlans" in source

    assert "applyPlanDeepLink" in source

    # The linked plan must drive the dependent selectors.
    assert "villageSelect.value" in source
    assert "committeeSelect.value" in source
    assert "planSelect.value" in source

    # Invalid/stale links should not crash the form.
    assert "Could not find that assigned action plan" in source

def test_da_work_hub_css_contract():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]

    source = (
        root
        / "app"
        / "static"
        / "css"
        / "app.css"
    ).read_text(encoding="utf-8")

    assert ".work-tabs" in source
    assert ".work-tab" in source
    assert ".work-tab.is-active" in source
    assert ".work-count" in source
    assert ".da-work-card" in source
    assert ".da-work-go" in source
    assert ".upcoming-work" in source
    assert ".da-work-empty" in source

    assert "@media" in source


def test_base_template_contains_da_field_shell_contract():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    source = (
        root
        / "app"
        / "templates"
        / "base.html"
    ).read_text(encoding="utf-8")

    assert 'class="da-field-appbar"' in source
    assert 'class="da-field-bottom-nav"' in source
    assert "data-da-entry-menu" in source
    assert "data-da-more-menu" in source

    for label in ("Entry", "Plans", "Reports", "More"):
        assert f">{label}<" in source

def test_da_primary_action_uses_one_time_attention_effect():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]

    js = (
        root
        / "app"
        / "static"
        / "js"
        / "action-plans.js"
    ).read_text(encoding="utf-8")

    css = (
        root
        / "app"
        / "static"
        / "css"
        / "app.css"
    ).read_text(encoding="utf-8")

    assert "is-attention-pulse" in js
    assert "animationend" in js
    assert "prefers-reduced-motion: reduce" in js

    assert ".is-attention-pulse" in css
    assert "@keyframes mv-attention-pulse" in css