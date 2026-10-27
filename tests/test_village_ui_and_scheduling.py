"""Regression cases for the October 2026 field-work redesign."""
from __future__ import annotations

from datetime import date

from app.admin_api import RESOURCES
from app.extensions import db
from app.models import DA, PC, ActionPlan, ActionPlanType, Cluster, Committee, Role, User, Village
from app.services.monthly_plans import fill_blank_village_schedules
from app.timeutils import current_month


def test_admin_attendance_resource_keeps_correct_metadata():
    spec = RESOURCES["attendance-entries"]
    assert spec.model.__name__ == "AttendanceEntry"
    assert spec.label == "Attendance Entries"
    assert any(field.name == "committee_id" for field in spec.fields)


def test_village_date_fills_unscheduled_siblings_without_overwriting_existing_dates(app):
    with app.app_context():
        month = current_month()
        day = date(month.year, month.month, 10)
        different = date(month.year, month.month, 12)
        pc = PC(full_name="PC Village Date", cluster=Cluster.PDTC)
        da = DA(full_name="DA Village Date", pc=pc)
        village = Village(name="Example Village", da=da)
        source_committee = Committee(name="Water", village=village)
        empty_committee = Committee(name="Health", village=village)
        explicit_committee = Committee(name="Farmer", village=village)
        additional_committee = Committee(name="Youth", village=village)
        user = User(email="pc-village-date@example.org", role=Role.PC, display_name="PC", pc=pc)
        user.set_password("StrongPassword456")
        db.session.add_all([pc, da, village, source_committee, empty_committee, explicit_committee, additional_committee, user])
        db.session.flush()
        source = ActionPlan(committee=source_committee, title="Water", plan_month=month,
                            assigned_date=day, plan_type=ActionPlanType.ATTENDANCE,
                            assigned_by_user_id=user.id)
        draft = ActionPlan(committee=empty_committee, title="Health", plan_month=month,
                           assigned_date=None, plan_type=None)
        explicit = ActionPlan(committee=explicit_committee, title="Farmer", plan_month=month,
                              assigned_date=different, plan_type=ActionPlanType.ATTENDANCE,
                              assigned_by_user_id=user.id)
        db.session.add_all([source, draft, explicit])
        db.session.flush()
        changed = fill_blank_village_schedules(source, user)
        db.session.commit()
        assert set(changed) == {empty_committee.id, additional_committee.id}
        assert draft.assigned_date == day
        assert draft.plan_type == ActionPlanType.ATTENDANCE
        assert explicit.assigned_date == different
        created = db.session.scalar(db.select(ActionPlan).where(ActionPlan.committee_id == additional_committee.id))
        assert created is not None and created.assigned_date == day
        assert fill_blank_village_schedules(source, user) == []


def test_da_pc_can_sign_in_with_registered_mobile_and_access_own_pages(client, app):
    with app.app_context():
        pc = PC(full_name="Login PC", cluster=Cluster.CSRB)
        da = DA(full_name="Login DA", pc=pc)
        pc_user = User(email="pc-login@example.org", mobile="+919876543201",
                       display_name="Login PC", role=Role.PC, pc=pc)
        da_user = User(email="da-login@example.org", mobile="9876543202",
                       display_name="Login DA", role=Role.DA, da=da)
        pc_user.set_password("TestPassword123")
        da_user.set_password("TestPassword123")
        db.session.add_all([pc, da, pc_user, da_user])
        db.session.commit()
    for mobile in ("98765 43201", "+91 98765-43202"):
        response = client.post("/login", data={"identifier": mobile, "password": "TestPassword123"})
        assert response.status_code in {302, 303}
        assert client.get("/action-plans").status_code == 200
        assert client.get("/api/v1/admin/resources").status_code == 403
        client.post("/logout")
