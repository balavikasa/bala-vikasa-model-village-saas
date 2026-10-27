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


def test_da_work_queue_groups_all_committees_by_village_and_excludes_specials(app):
    """The new DA hub offers one GO per village, never per committee.

    Historical Specials and old-month tasks remain in the database but are
    not executable village-attendance assignments for the selected month.
    """
    with app.app_context():
        pc = PC(full_name="Test PC", cluster=Cluster.CSRB)
        da = DA(full_name="Test DA", pc=pc)
        village_a = Village(name="Today Village", da=da)
        village_b = Village(name="Pending Village", da=da)
        village_c = Village(name="Upcoming Village", da=da)
        a_today = Committee(name="Environment", village=village_a)
        a_pending = Committee(name="Health", village=village_a)
        a_upcoming = Committee(name="Farmer", village=village_a)
        a_draft = Committee(name="Water", village=village_a)
        a_rollover = Committee(name="Education", village=village_a)
        b_pending = Committee(name="VDC", village=village_b)
        c_upcoming = Committee(name="Women", village=village_c)
        c_specials = Committee(name="Youth", village=village_c)
        user = User(email="queue-da@example.org", role=Role.DA, display_name="Queue DA", da=da)
        user.set_password("1234")
        db.session.add_all([
            pc, da, village_a, village_b, village_c,
            a_today, a_pending, a_upcoming, a_draft, a_rollover,
            b_pending, c_upcoming, c_specials, user,
        ])
        db.session.flush()

        def plan(committee, month, scheduled, kind=ActionPlanType.ATTENDANCE):
            return ActionPlan(
                committee=committee,
                title=committee.name,
                plan_month=month,
                plan_type=kind,
                assigned_date=scheduled,
                assigned_by_user_id=user.id,
            )

        today_plan = plan(a_today, date(2026, 8, 1), date(2026, 8, 15))
        a_pending_plan = plan(a_pending, date(2026, 8, 1), date(2026, 8, 10))
        a_upcoming_plan = plan(a_upcoming, date(2026, 8, 1), date(2026, 8, 25))
        draft_plan = plan(a_draft, date(2026, 8, 1), None, None)
        old_plan = plan(a_rollover, date(2026, 7, 1), date(2026, 7, 31))
        pending_plan = plan(b_pending, date(2026, 8, 1), date(2026, 8, 12))
        upcoming_plan = plan(c_upcoming, date(2026, 8, 1), date(2026, 8, 25))
        specials_plan = plan(c_specials, date(2026, 8, 1), date(2026, 8, 22), ActionPlanType.SPECIALS)
        db.session.add_all([
            today_plan, a_pending_plan, a_upcoming_plan,
            pending_plan, upcoming_plan, draft_plan, old_plan, specials_plan,
        ])
        db.session.commit()

        queue = monthly_plans.da_work_queue(user, today=date(2026, 8, 15))
        assert queue["counts"] == {"today": 1, "pending": 1, "upcoming": 1}
        assert [item["village_id"] for item in queue["today"]] == [village_a.id]
        assert [item["village_id"] for item in queue["pending"]] == [village_b.id]
        assert [item["village_id"] for item in queue["upcoming"]] == [village_c.id]
        today_card = queue["today"][0]
        assert today_card["plan_id"] == today_plan.id
        assert today_card["committee_count"] == 3
        assert today_card["go_url"] == f"/field/attendance?village={village_a.id}"
        assert queue["pending"][0]["plan_id"] == pending_plan.id
        assert queue["upcoming"][0]["plan_id"] == upcoming_plan.id
        assert queue["pending"][0]["days_overdue"] == 3

        all_ids = {
            item["plan_id"] for category in ("today", "pending", "upcoming")
            for item in queue[category]
        }
        assert all_ids.isdisjoint({draft_plan.id, old_plan.id, specials_plan.id})
        assert len(all_ids) == 3
