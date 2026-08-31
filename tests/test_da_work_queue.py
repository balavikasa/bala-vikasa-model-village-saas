from __future__ import annotations

from datetime import date

import app.services.monthly_plans as monthly_plans
from app.extensions import db
from app.models import (
    DA,
    PC,
    ActionPlan,
    ActionPlanType,
    Cluster,
    Committee,
    Role,
    User,
    Village,
)


def test_da_work_queue_classifies_today_pending_and_upcoming(app):
    with app.app_context():
        pc = PC(
            full_name="Test PC",
            cluster=Cluster.CSRB,
        )

        da = DA(
            full_name="Test DA",
            pc=pc,
        )

        village = Village(
            name="Test Village",
            da=da,
        )

        today_committee = Committee(
            name="Environment",
            village=village,
        )

        pending_committee = Committee(
            name="Health",
            village=village,
        )

        rollover_committee = Committee(
            name="Education",
            village=village,
        )

        upcoming_committee = Committee(
            name="Farmer",
            village=village,
        )

        draft_committee = Committee(
            name="Water",
            village=village,
        )

        user = User(
            email="queue-da@example.org",
            role=Role.DA,
            display_name="Queue DA",
            da=da,
        )
        user.set_password("1234")

        db.session.add_all(
            [
                pc,
                da,
                village,
                today_committee,
                pending_committee,
                rollover_committee,
                upcoming_committee,
                draft_committee,
                user,
            ]
        )
        db.session.flush()

        today_plan = ActionPlan(
            committee=today_committee,
            title=today_committee.name,
            plan_month=date(2026, 8, 1),
            plan_type=ActionPlanType.ATTENDANCE,
            assigned_date=date(2026, 8, 15),
            assigned_by_user_id=user.id,
        )

        pending_plan = ActionPlan(
            committee=pending_committee,
            title=pending_committee.name,
            plan_month=date(2026, 8, 1),
            plan_type=ActionPlanType.SPECIALS,
            assigned_date=date(2026, 8, 10),
            assigned_by_user_id=user.id,
        )

        # Important rollover case:
        # unfinished work from a previous month must remain Pending.
        rollover_plan = ActionPlan(
            committee=rollover_committee,
            title=rollover_committee.name,
            plan_month=date(2026, 7, 1),
            plan_type=ActionPlanType.ATTENDANCE,
            assigned_date=date(2026, 7, 31),
            assigned_by_user_id=user.id,
        )

        upcoming_plan = ActionPlan(
            committee=upcoming_committee,
            title=upcoming_committee.name,
            plan_month=date(2026, 8, 1),
            plan_type=ActionPlanType.SPECIALS,
            assigned_date=date(2026, 8, 25),
            assigned_by_user_id=user.id,
        )

        # Drafts must never become DA work items.
        draft_plan = ActionPlan(
            committee=draft_committee,
            title=draft_committee.name,
            plan_month=date(2026, 8, 1),
            plan_type=None,
            assigned_date=None,
            assigned_by_user_id=user.id,
        )

        db.session.add_all(
            [
                today_plan,
                pending_plan,
                rollover_plan,
                upcoming_plan,
                draft_plan,
            ]
        )
        db.session.commit()

        assert hasattr(monthly_plans, "da_work_queue")

        queue = monthly_plans.da_work_queue(
            user,
            today=date(2026, 8, 15),
        )

        assert [item["plan_id"] for item in queue["today"]] == [
            today_plan.id
        ]

        assert {
            item["plan_id"]
            for item in queue["pending"]
        } == {
            pending_plan.id,
            rollover_plan.id,
        }

        assert [
            item["plan_id"]
            for item in queue["upcoming"]
        ] == [
            upcoming_plan.id
        ]

        all_ids = {
            item["plan_id"]
            for group in (
                queue["today"],
                queue["pending"],
                queue["upcoming"],
            )
            for item in group
        }

        assert draft_plan.id not in all_ids

        today_item = queue["today"][0]

        assert today_item["village_name"] == "Test Village"
        assert today_item["committee_name"] == "Environment"
        assert today_item["plan_type"] == "Attendance"
        assert today_item["assigned_date"] == "2026-08-15"
        assert today_item["go_url"] == (
            f"/field/attendance?plan={today_plan.id}"
        )

        pending_special = next(
            item
            for item in queue["pending"]
            if item["plan_id"] == pending_plan.id
        )

        assert pending_special["plan_type"] == "Specials"
        assert pending_special["go_url"] == (
            f"/field/specials?plan={pending_plan.id}"
        )

        assert queue["counts"] == {
            "today": 1,
            "pending": 2,
            "upcoming": 1,
        }