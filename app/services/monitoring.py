from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import (
    DA,
    ActionPlan,
    AttendanceEntry,
    Committee,
    Role,
    User,
    Village,
    VillageAttendanceVisit,
)
from ..scoping import inherited_cluster, scoped_select
from ..timeutils import current_month, local_today
from .visit_presentation import daily_visit_trend, visible_attendance


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
               VillageAttendanceVisit.visit_date < end,
               VillageAttendanceVisit.is_enabled.is_(True),
               VillageAttendanceVisit.is_deleted.is_(False))
        .options(selectinload(VillageAttendanceVisit.entries))
    ).unique().all())
    # The assigned-village denominator must not grow when a DA submits an
    # authorised Other-village visit. Those visits are tracked separately.
    visible_ids = {v.id for v in villages}
    visited_ids = {v.village_id for v in visits if v.is_enabled and not v.is_deleted}
    done = len(visible_ids & visited_ids)
    other_visited = len(visited_ids - visible_ids) if user.role == Role.DA else 0
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
    breakdown = {"Done": done, "Not done": pending}
    if other_visited:
        breakdown["Other village visits"] = other_visited
    return {
        "counts": {
            "villages": len(visible_ids),
            "committees": len(committees),
            "villages_done": done,
            "villages_pending": pending,
            "other_villages_visited": other_visited,
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
        "status_breakdown": breakdown,
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

    def evidence_photo_url(entry: Any) -> str | None:
        if not entry or not entry.photo_path:
            return None
        return f"/api/v1/photos/attendance/{entry.id}"

    village_query = scoped_select(Village, user)
    if user.role == Role.DA and user.da_id is not None:
        # An Other-village visit does not transfer ownership. It grants the
        # submitting DA visibility of their own completed field evidence.
        visited_elsewhere = db.select(VillageAttendanceVisit.village_id).where(
            VillageAttendanceVisit.submitted_by_user_id == user.id,
            VillageAttendanceVisit.is_enabled.is_(True),
            VillageAttendanceVisit.is_deleted.is_(False),
        )
        village_query = db.select(Village).where(
            Village.is_enabled.is_(True),
            Village.is_deleted.is_(False),
            or_(Village.da_id == user.da_id, Village.id.in_(visited_elsewhere)),
        )
    villages = list(
        db.session.scalars(
            village_query
            .options(
                selectinload(Village.da).selectinload(DA.pc),
                selectinload(Village.committees)
                .selectinload(Committee.action_plans)
                .selectinload(ActionPlan.attendance_entry),
                selectinload(Village.committees)
                .selectinload(Committee.action_plans)
                .selectinload(ActionPlan.specials_entry),
                selectinload(Village.attendance_entries).selectinload(AttendanceEntry.village_visit),
                # Archived Specials are kept for historical reports, not live visit evidence.
            )
            .order_by(Village.name)
        ).unique()
    )

    markers: list[dict[str, Any]] = []
    today = local_today()

    for village in villages:
        outside = user.role == Role.DA and village.da_id != user.da_id
        attendance = visible_attendance(
            village.attendance_entries, submitter_id=user.id if outside else None
        )
        # The current program has one DA-led attendance visit, not Specials.
        # Keep archived Specials in the DB/reports, but do not project them as
        # current field GPS or photographic evidence.
        latest_evidence = max(attendance, key=lambda item: (item.visit_date, item.id), default=None)
        latest_located = max(
            (item for item in attendance if valid_coordinates(item.latitude, item.longitude)),
            key=lambda item: (item.visit_date, item.id),
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

        overall = "Visited" if any(
            e.is_enabled and not e.is_deleted and
            e.visit_date.year == today.year and e.visit_date.month == today.month
            for e in attendance
        ) else "Not visited"

        markers.append(
            {
                "id": village.id,
                "name": village.name,
                "cluster": village.da.pc.cluster.value,
                "da_name": village.da.full_name,
                "outside_assignment": bool(user.role == Role.DA and village.da_id != user.da_id),
                "latitude": latitude,
                "longitude": longitude,
                "location_source": location_source,
                "last_visit_date": (
                    latest_evidence.visit_date.isoformat()
                    if latest_evidence
                    else None
                ),
                "evidence_type": (
                    "Attendance" if latest_evidence else None
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
        VillageAttendanceVisit.is_enabled.is_(True),
        VillageAttendanceVisit.is_deleted.is_(False),
    ).options(selectinload(VillageAttendanceVisit.entries))).unique().all()
    committee_totals: Counter[str] = Counter()
    status_by_cluster: dict[str, Counter[str]] = defaultdict(Counter)
    assigned_ids = set(db.session.scalars(scoped_select(Village, user).with_only_columns(Village.id)))
    counted_ids: set[int] = set()
    for visit in visits:
        if visit.village_id in assigned_ids and visit.village_id not in counted_ids:
            status_by_cluster[inherited_cluster(visit.village) or "Unknown"]["Done"] += 1
            counted_ids.add(visit.village_id)
        for entry in visit.entries:
            if entry.is_enabled and not entry.is_deleted:
                committee_totals[entry.committee.committee_type or "Other"] += 1
    # A seven-day window can span a month boundary; query it independently.
    today = local_today()
    recent_visits = list(db.session.scalars(
        scoped_select(VillageAttendanceVisit, user).where(
            VillageAttendanceVisit.visit_date >= today - timedelta(days=6),
            VillageAttendanceVisit.visit_date <= today,
            VillageAttendanceVisit.is_enabled.is_(True),
            VillageAttendanceVisit.is_deleted.is_(False),
        ).options(selectinload(VillageAttendanceVisit.entries))
    ).unique().all())
    return {
        **summary,
        "daily_trend": daily_visit_trend(recent_visits, today),
        "committee_aggregates": dict(committee_totals),
        "status_by_cluster": {cluster: dict(values) for cluster, values in status_by_cluster.items()},
    }


def recent_village_activity(user: User) -> dict[str, Any]:
    """Six recent role-scoped DA visits and pending assigned villages."""
    month = current_month()
    nxt = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    assigned = list(db.session.scalars(scoped_select(Village, user).order_by(Village.name)))
    assigned = [v for v in assigned if v.is_enabled and not v.is_deleted]
    visits = list(db.session.scalars(
        scoped_select(VillageAttendanceVisit, user)
        .where(VillageAttendanceVisit.is_enabled.is_(True),
               VillageAttendanceVisit.is_deleted.is_(False))
        .options(selectinload(VillageAttendanceVisit.village),
                 selectinload(VillageAttendanceVisit.entries))
        .order_by(VillageAttendanceVisit.submitted_at.desc())
        .limit(120)
    ).unique().all())
    visited = {v.village_id for v in visits if month <= v.visit_date < nxt}
    recent = []
    for visit in visits[:6]:
        count = sum(e.male_count + e.female_count for e in visit.entries
                    if e.is_enabled and not e.is_deleted)
        recent.append({
            'id': visit.id, 'village': visit.village.name,
            'date': visit.visit_date.isoformat(), 'people': count,
            'outside_assignment': bool(user.role == Role.DA and user.da_id is not None
                                       and visit.village.da_id != user.da_id),
            'report_url': f'/reports/village/{visit.id}',
        })
    pending = [
        {'id': village.id, 'name': village.name, 'url': f'/directory/village/{village.id}'}
        for village in assigned if village.id not in visited
    ]
    return {'recent': recent, 'pending': pending[:8], 'pending_total': len(pending)}
