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
    VillageAttendanceVisit,
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
    """Current-month operational KPIs from real village visits, not PC plans."""
    month = current_month()
    if month.month == 12:
        end = date(month.year + 1, 1, 1)
    else:
        end = date(month.year, month.month + 1, 1)
    villages = list(db.session.scalars(scoped_select(Village, user)).all())
    committees = list(db.session.scalars(scoped_select(Committee, user)).all())
    visits = list(db.session.scalars(
        scoped_select(VillageAttendanceVisit, user)
        .where(VillageAttendanceVisit.visit_date >= month,
               VillageAttendanceVisit.visit_date < end)
        .options(selectinload(VillageAttendanceVisit.entries))
    ).unique().all())
    visible_ids = {v.id for v in villages}
    # For DAs, their visits to another assigned village remain on their own KPI.
    if user.role.value == "da":
        visible_ids.update(visit.village_id for visit in visits)
    done = len({v.village_id for v in visits if v.is_enabled and not v.is_deleted})
    gender = {"Male": 0, "Female": 0}
    entries_count = 0
    for visit in visits:
        for entry in visit.entries:
            if entry.is_enabled and not entry.is_deleted:
                entries_count += 1
                gender["Male"] += entry.male_count
                gender["Female"] += entry.female_count
    clusters = Counter(inherited_cluster(village) for village in villages)
    pending = max(0, len(visible_ids) - done)
    return {
        "counts": {
            "villages": len(visible_ids),
            "committees": len(committees),
            "villages_done": done,
            "villages_pending": pending,
            "attendance_entries": entries_count,
            "people_attended": sum(gender.values()),
            "new_members": sum(
                v.new_members_count if v.visit_month is not None
                else sum(e.new_members_count for e in v.entries if e.is_enabled and not e.is_deleted)
                for v in visits
            ),
            "action_plans": len(scoped_action_plans(user)),  # retained for historical views
            "specials_entries": 0, "participants": 0,
        },
        "status_breakdown": {"Done": done, "Not done": pending},
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

        overall = "On-time" if any(
            e.is_enabled and not e.is_deleted and
            e.visit_date.year == today.year and e.visit_date.month == today.month
            for e in attendance
        ) else "Draft"

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
    month = current_month()
    nxt = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    visits = db.session.scalars(scoped_select(VillageAttendanceVisit, user).where(
        VillageAttendanceVisit.visit_date >= month,
        VillageAttendanceVisit.visit_date < nxt,
    ).options(selectinload(VillageAttendanceVisit.entries))).unique().all()
    committee_totals: Counter[str] = Counter()
    status_by_cluster: dict[str, Counter[str]] = defaultdict(Counter)
    for visit in visits:
        status_by_cluster[inherited_cluster(visit.village) or "Unknown"]["Done"] += 1
        for entry in visit.entries:
            if entry.is_enabled and not entry.is_deleted:
                committee_totals[entry.committee.committee_type or "Other"] += 1
    return {
        **summary,
        "committee_aggregates": dict(committee_totals),
        "status_by_cluster": {cluster: dict(values) for cluster, values in status_by_cluster.items()},
    }
