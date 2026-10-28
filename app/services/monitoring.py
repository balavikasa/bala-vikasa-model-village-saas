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
    def valid_coordinates(latitude: Any, longitude: Any) -> bool:
        if latitude is None or longitude is None:
            return False
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (TypeError, ValueError):
            return False
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return False
        return not (abs(lat) < 0.000001 and abs(lon) < 0.000001)

    def evidence_date(entry: Any) -> date:
        return entry.visit_date if hasattr(entry, "visit_date") else entry.event_date

    def evidence_type(entry: Any) -> str:
        return "Attendance" if hasattr(entry, "visit_date") else "Specials"

    def evidence_photo_url(entry: Any) -> str | None:
        if not entry or not entry.photo_path:
            return None
        kind = "attendance" if hasattr(entry, "visit_date") else "specials"
        return f"/api/v1/photos/{kind}/{entry.id}"

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
                selectinload(Village.specials_entries),
            )
            .order_by(Village.name)
        ).unique()
    )

    markers: list[dict[str, Any]] = []
    today = local_today()

    for village in villages:
        attendance = [
            item
            for item in village.attendance_entries
            if item.is_enabled and not item.is_deleted
        ]
        specials = [
            item
            for item in village.specials_entries
            if item.is_enabled and not item.is_deleted
        ]
        evidence_rows = [*attendance, *specials]

        latest_evidence = max(
            evidence_rows,
            key=lambda item: (evidence_date(item), item.id),
            default=None,
        )
        located_evidence = [
            item
            for item in evidence_rows
            if valid_coordinates(item.latitude, item.longitude)
        ]
        latest_located = max(
            located_evidence,
            key=lambda item: (evidence_date(item), item.id),
            default=None,
        )

        if latest_located is not None:
            latitude = latest_located.latitude
            longitude = latest_located.longitude
            location_source = "field-evidence"
        elif valid_coordinates(village.latitude, village.longitude):
            latitude = village.latitude
            longitude = village.longitude
            location_source = "village-master"
        else:
            latitude = None
            longitude = None
            location_source = None

        plans = [
            plan
            for committee in village.committees
            if committee.is_enabled and not committee.is_deleted
            for plan in committee.action_plans
            if (
                plan.is_enabled
                and not plan.is_deleted
                and plan.plan_month == today.replace(day=1)
            )
        ]
        statuses = [action_plan_status(plan, today) for plan in plans]
        priority = [
            "Failure",
            "Postponed",
            "Early",
            "Due today",
            "Scheduled",
            "On-time",
            "Draft",
        ]
        overall = next((value for value in priority if value in statuses), "No plan")

        markers.append(
            {
                "id": village.id,
                "name": village.name,
                "cluster": village.da.pc.cluster.value,
                "da_name": village.da.full_name,
                "latitude": latitude,
                "longitude": longitude,
                "location_source": location_source,
                "last_visit_date": (
                    evidence_date(latest_evidence).isoformat()
                    if latest_evidence
                    else None
                ),
                "evidence_type": (
                    evidence_type(latest_evidence)
                    if latest_evidence
                    else None
                ),
                "status": overall,
                "photo_url": evidence_photo_url(latest_evidence),
                "committee_count": len(
                    [
                        committee
                        for committee in village.committees
                        if committee.is_enabled and not committee.is_deleted
                    ]
                ),
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
