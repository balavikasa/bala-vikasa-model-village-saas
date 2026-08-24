from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any

from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import (
    DA,
    ActionPlan,
    Committee,
    User,
    Village,
)
from ..scoping import inherited_cluster, scoped_select
from ..timeutils import current_month, local_today


def action_plan_status(plan: ActionPlan, today: date | None = None) -> str:
    today = today or local_today()
    if plan.attendance_entry and not plan.attendance_entry.is_deleted:
        return plan.attendance_entry.status.value
    if plan.specials_entry and not plan.specials_entry.is_deleted:
        return plan.specials_entry.status.value if plan.specials_entry.status else "Completed"
    if not plan.is_executable:
        return "Draft"
    if plan.assigned_date < today:
        return "Failure"
    if plan.assigned_date == today:
        return "Due today"
    return "Scheduled"


def scoped_action_plans(user: User, month: date | None = None) -> list[ActionPlan]:
    selected_month = (month or current_month()).replace(day=1)
    stmt = (
        scoped_select(ActionPlan, user)
        .where(ActionPlan.plan_month == selected_month)
        .options(
            selectinload(ActionPlan.attendance_entry),
            selectinload(ActionPlan.specials_entry),
            selectinload(ActionPlan.committee)
            .selectinload(Committee.village)
            .selectinload(Village.da)
            .selectinload(DA.pc),
        )
        .order_by(ActionPlan.assigned_date.asc().nullslast(), ActionPlan.id)
    )
    return list(db.session.scalars(stmt).unique())


def dashboard_summary(user: User) -> dict[str, Any]:
    villages = list(
        db.session.scalars(
            scoped_select(Village, user).options(selectinload(Village.da).selectinload(DA.pc))
        ).unique()
    )
    committees = list(db.session.scalars(scoped_select(Committee, user)).all())
    plans = scoped_action_plans(user)
    # Dashboard activity is tied to the current monthly plan occurrence, not an
    # all-time entry count. This keeps monthly KPIs internally consistent even
    # when an Early visit occurs before the calendar month begins.
    attendance = [
        plan.attendance_entry
        for plan in plans
        if plan.attendance_entry
        and plan.attendance_entry.is_enabled
        and not plan.attendance_entry.is_deleted
    ]
    specials = [
        plan.specials_entry
        for plan in plans
        if plan.specials_entry
        and plan.specials_entry.is_enabled
        and not plan.specials_entry.is_deleted
    ]

    statuses = Counter(action_plan_status(plan) for plan in plans)
    clusters = Counter(inherited_cluster(village) for village in villages)
    gender = {
        "Male": sum(row.male_count for row in attendance),
        "Female": sum(row.female_count for row in attendance),
    }
    return {
        "counts": {
            "villages": len(villages),
            "committees": len(committees),
            "action_plans": len(plans),
            "attendance_entries": len(attendance),
            "specials_entries": len(specials),
            "participants": sum(row.participant_count for row in specials),
        },
        "status_breakdown": dict(statuses),
        "cluster_breakdown": {key: value for key, value in clusters.items() if key},
        "gender_distribution": gender,
    }


def map_markers(user: User) -> list[dict[str, Any]]:
    villages = list(
        db.session.scalars(
            scoped_select(Village, user)
            .options(
                selectinload(Village.da).selectinload(DA.pc),
                selectinload(Village.committees)
                .selectinload(Committee.action_plans)
                .selectinload(ActionPlan.attendance_entry),
                selectinload(Village.committees)
                .selectinload(Committee.action_plans)
                .selectinload(ActionPlan.specials_entry),
                selectinload(Village.attendance_entries),
            )
            .order_by(Village.name)
        ).unique()
    )
    markers: list[dict[str, Any]] = []
    today = local_today()
    for village in villages:
        entries = [item for item in village.attendance_entries if item.is_enabled and not item.is_deleted]
        latest = max(entries, key=lambda item: (item.visit_date, item.id), default=None)
        plans = [
            plan
            for committee in village.committees
            if committee.is_enabled and not committee.is_deleted
            for plan in committee.action_plans
            if plan.is_enabled and not plan.is_deleted and plan.plan_month == today.replace(day=1)
        ]
        statuses = [action_plan_status(plan, today) for plan in plans]
        priority = ["Failure", "Postponed", "Early", "Due today", "Scheduled", "On-time", "Draft"]
        overall = next((value for value in priority if value in statuses), "No plan")
        markers.append(
            {
                "id": village.id,
                "name": village.name,
                "cluster": village.da.pc.cluster.value,
                "da_name": village.da.full_name,
                "latitude": village.latitude,
                "longitude": village.longitude,
                "last_visit_date": latest.visit_date.isoformat() if latest else None,
                "status": overall,
                "photo_url": f"/api/v1/photos/attendance/{latest.id}" if latest and latest.photo_path else None,
                "committee_count": len([c for c in village.committees if c.is_enabled and not c.is_deleted]),
            }
        )
    return markers


def dashboard_series(user: User) -> dict[str, Any]:
    summary = dashboard_summary(user)
    plans = scoped_action_plans(user)
    committee_totals: Counter[str] = Counter()
    status_by_cluster: dict[str, Counter[str]] = defaultdict(Counter)
    for plan in plans:
        committee_totals[plan.committee.committee_type or "Other"] += 1
        status_by_cluster[inherited_cluster(plan) or "Unknown"][action_plan_status(plan)] += 1

    return {
        **summary,
        "committee_aggregates": dict(committee_totals),
        "status_by_cluster": {cluster: dict(values) for cluster, values in status_by_cluster.items()},
    }
