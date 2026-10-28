from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import (
    DA,
    PC,
    PM,
    ActionPlan,
    AttendanceEntry,
    Committee,
    User,
    Village,
)
from ..scoping import scoped_select
from ..timeutils import current_month
from .monthly_plans import action_plan_status


def _current_month() -> date:
    return current_month()


def _active_entries(village: Village) -> list[AttendanceEntry]:
    return [entry for entry in village.attendance_entries if entry.is_enabled and not entry.is_deleted]


def _village_visit_summary(village: Village, month: date) -> dict[str, Any]:
    entries = _active_entries(village)
    current = [entry for entry in entries if entry.visit_date.year == month.year
               and entry.visit_date.month == month.month]
    latest = max(entries, key=lambda entry: (entry.visit_date, entry.id), default=None)
    distinct_visits = {(entry.village_visit_id or ("legacy", entry.visit_date)) for entry in entries}
    return {
        "visited": bool(current),
        "visits": len(distinct_visits),
        "latest": latest.visit_date.isoformat() if latest else None,
        "people": sum(entry.total_count for entry in current),
    }


def _status_counts(plans: list[ActionPlan]) -> dict[str, int]:
    counts = Counter(action_plan_status(plan) for plan in plans)
    order = ("Draft", "Scheduled", "Due today", "Early", "On-time", "Postponed", "Failure")
    return {key: counts.get(key, 0) for key in order}


def _plan_rows(plans: list[ActionPlan], limit: int = 12) -> list[dict[str, Any]]:
    rows = []
    for plan in sorted(
        plans,
        key=lambda p: (p.assigned_date or date.max, p.committee.village.name.casefold(), p.committee.name.casefold()),
    )[:limit]:
        village = plan.committee.village
        rows.append(
            {
                "id": plan.id,
                "assigned_date": plan.assigned_date.isoformat() if plan.assigned_date else None,
                "type": plan.plan_type.value if plan.plan_type else "Draft",
                "status": action_plan_status(plan),
                "village": village.name,
                "committee": plan.committee.name,
                "report_url": f"/reports/plan/{plan.id}",
            }
        )
    return rows


def da_profile(user: User, da_id: int) -> dict[str, Any] | None:
    stmt = (
        scoped_select(DA, user)
        .where(DA.id == da_id)
        .options(
            selectinload(DA.pc),
            selectinload(DA.villages).selectinload(Village.attendance_entries),
            selectinload(DA.villages)
            .selectinload(Village.committees)
            .selectinload(Committee.members),
            selectinload(DA.villages)
            .selectinload(Village.committees)
            .selectinload(Committee.action_plans)
            .selectinload(ActionPlan.attendance_entry),
            selectinload(DA.villages)
            .selectinload(Village.committees)
            .selectinload(Committee.action_plans)
            .selectinload(ActionPlan.specials_entry),
        )
    )
    da = db.session.scalar(stmt)
    if da is None:
        return None
    villages = [v for v in da.villages if v.is_enabled and not v.is_deleted]
    committees = [
        c for v in villages for c in v.committees if c.is_enabled and not c.is_deleted
    ]
    members = [
        member
        for committee in committees
        for member in committee.members
        if member.is_enabled and not member.is_deleted
    ]
    month = _current_month()
    village_summaries = {v.id: _village_visit_summary(v, month) for v in villages}
    visited_count = sum(1 for item in village_summaries.values() if item["visited"])
    plans = [
        plan
        for committee in committees
        for plan in committee.action_plans
        if plan.is_enabled and not plan.is_deleted and plan.plan_month == month
    ]
    return {
        "kind": "DA",
        "id": da.id,
        "name": da.full_name,
        "cluster": da.pc.cluster.value,
        "pc": {"id": da.pc.id, "name": da.pc.full_name},
        "email": da.email,
        "mobile": da.mobile,
        "counts": {
            "villages": len(villages),
            "committees": len(committees),
            "members": len(members),
            "villages_visited": visited_count,
            "villages_pending": len(villages) - visited_count,
        },
        "status": {"Visited": visited_count, "Not visited": len(villages) - visited_count},
        "villages": [
            {
                "id": village.id,
                "name": village.name,
                "code": village.code,
                "mandal": village.mandal,
                "district": village.district,
                "latitude": village.latitude,
                "longitude": village.longitude,
                "committee_count": sum(1 for c in village.committees if c.is_enabled and not c.is_deleted),
                "member_count": sum(
                    1
                    for c in village.committees
                    if c.is_enabled and not c.is_deleted
                    for m in c.members
                    if m.is_enabled and not m.is_deleted
                ),
                "url": f"/directory/village/{village.id}",
                "visited": village_summaries[village.id]["visited"],
                "last_visit": village_summaries[village.id]["latest"],
            }
            for village in sorted(villages, key=lambda item: item.name.casefold())
        ],
        "plans": _plan_rows(plans),
    }


def village_profile(user: User, village_id: int) -> dict[str, Any] | None:
    stmt = (
        scoped_select(Village, user)
        .where(Village.id == village_id)
        .options(
            selectinload(Village.da).selectinload(DA.pc),
            selectinload(Village.attendance_entries),
            selectinload(Village.committees).selectinload(Committee.members),
            selectinload(Village.committees)
            .selectinload(Committee.action_plans)
            .selectinload(ActionPlan.attendance_entry),
            selectinload(Village.committees)
            .selectinload(Committee.action_plans)
            .selectinload(ActionPlan.specials_entry),
        )
    )
    village = db.session.scalar(stmt)
    if village is None:
        return None
    committees = [c for c in village.committees if c.is_enabled and not c.is_deleted]
    month = _current_month()
    visit_summary = _village_visit_summary(village, month)
    entries = _active_entries(village)
    committee_rows = []
    total_members = 0
    for committee in sorted(committees, key=lambda c: c.name.casefold()):
        members = [m for m in committee.members if m.is_enabled and not m.is_deleted]
        total_members += len(members)
        designations = Counter(m.designation or "Not stated" for m in members)
        latest = max((e for e in entries if e.committee_id == committee.id),
                     key=lambda e: (e.visit_date, e.id), default=None)
        current_attendance = [e for e in entries if e.committee_id == committee.id
                              and e.visit_date.year == month.year and e.visit_date.month == month.month]
        committee_rows.append(
            {
                "id": committee.id,
                "name": committee.name,
                "members": len(members),
                "designations": dict(designations),
                "last_visit": latest.visit_date.isoformat() if latest else None,
                "attendance": sum(e.total_count for e in current_attendance),
                "status": "Visited" if current_attendance else "Not visited",
                "report_url": (
                    f"/reports/village/{latest.village_visit_id}" if latest and latest.village_visit_id
                    else f"/reports/plan/{latest.action_plan_id}" if latest and latest.action_plan_id
                    else None
                ),
            }
        )
    return {
        "kind": "Village",
        "id": village.id,
        "name": village.name,
        "code": village.code,
        "gp_name": village.gp_name,
        "district": village.district,
        "mandal": village.mandal,
        "latitude": village.latitude,
        "longitude": village.longitude,
        "cluster": village.da.pc.cluster.value,
        "da": {"id": village.da.id, "name": village.da.full_name},
        "pc": {"id": village.da.pc.id, "name": village.da.pc.full_name},
        "counts": {"committees": len(committees), "members": total_members,
                   "visits": visit_summary["visits"], "attended_this_month": visit_summary["people"]},
        "status": {"Visited": int(visit_summary["visited"]),
                   "Not visited": int(not visit_summary["visited"])},
        "latest_visit": visit_summary["latest"],
        "committees": committee_rows,
    }


def pc_profile(user: User, pc_id: int) -> dict[str, Any] | None:
    stmt = (
        scoped_select(PC, user)
        .where(PC.id == pc_id)
        .options(
            selectinload(PC.das).selectinload(DA.villages).selectinload(Village.attendance_entries),
            selectinload(PC.das)
            .selectinload(DA.villages)
            .selectinload(Village.committees)
            .selectinload(Committee.members),
            selectinload(PC.das)
            .selectinload(DA.villages)
            .selectinload(Village.committees)
            .selectinload(Committee.action_plans)
            .selectinload(ActionPlan.attendance_entry),
            selectinload(PC.das)
            .selectinload(DA.villages)
            .selectinload(Village.committees)
            .selectinload(Committee.action_plans)
            .selectinload(ActionPlan.specials_entry),
        )
    )
    pc = db.session.scalar(stmt)
    if pc is None:
        return None
    das = [d for d in pc.das if d.is_enabled and not d.is_deleted]
    villages = [v for d in das for v in d.villages if v.is_enabled and not v.is_deleted]
    committees = [c for v in villages for c in v.committees if c.is_enabled and not c.is_deleted]
    members = [m for c in committees for m in c.members if m.is_enabled and not m.is_deleted]
    month = _current_month()
    village_summaries = {v.id: _village_visit_summary(v, month) for v in villages}
    visited_count = sum(int(row["visited"]) for row in village_summaries.values())
    plans = [p for c in committees for p in c.action_plans if p.is_enabled and not p.is_deleted and p.plan_month == month]
    da_rows = []
    for da in sorted(das, key=lambda d: d.full_name.casefold()):
        da_villages = [v for v in da.villages if v.is_enabled and not v.is_deleted]
        da_committees = [c for v in da_villages for c in v.committees if c.is_enabled and not c.is_deleted]
        da_done = sum(int(village_summaries[v.id]["visited"]) for v in da_villages)
        da_rows.append(
            {
                "id": da.id,
                "name": da.full_name,
                "villages": len(da_villages),
                "done": da_done,
                "pending": len(da_villages) - da_done,
                "url": f"/directory/da/{da.id}",
            }
        )
    return {
        "kind": "PC",
        "id": pc.id,
        "name": pc.full_name,
        "cluster": pc.cluster.value,
        "email": pc.email,
        "mobile": pc.mobile,
        "counts": {
            "das": len(das), "villages": len(villages), "committees": len(committees),
            "members": len(members), "villages_visited": visited_count,
            "villages_pending": len(villages) - visited_count
        },
        "status": {"Visited": visited_count, "Not visited": len(villages) - visited_count},
        "das": da_rows,
        "plans": _plan_rows(plans),
    }


def pm_profile(user: User, pm_id: int) -> dict[str, Any] | None:
    pm = db.session.scalar(scoped_select(PM, user).where(PM.id == pm_id))
    if pm is None:
        return None
    pcs = list(
        db.session.scalars(
            scoped_select(PC, user)
            .options(
                selectinload(PC.das)
                .selectinload(DA.villages)
                .selectinload(Village.committees)
            )
            .order_by(PC.full_name)
        ).unique()
    )
    villages = list(db.session.scalars(scoped_select(Village, user)).all())
    committees = list(db.session.scalars(scoped_select(Committee, user)).all())
    month = _current_month()
    plans = list(
        db.session.scalars(
            scoped_select(ActionPlan, user)
            .where(ActionPlan.plan_month == month)
            .options(
                selectinload(ActionPlan.attendance_entry),
                selectinload(ActionPlan.specials_entry),
                selectinload(ActionPlan.committee).selectinload(Committee.village),
            )
        ).unique()
    )
    return {
        "kind": "PM",
        "id": pm.id,
        "name": pm.full_name,
        "email": pm.email,
        "mobile": pm.mobile,
        "counts": {
            "pcs": len(pcs),
            "das": sum(len([d for d in pc.das if d.is_enabled and not d.is_deleted]) for pc in pcs),
            "villages": len(villages),
            "committees": len(committees),
            "plans": len(plans),
        },
        "status": _status_counts(plans),
        "pcs": [
            {
                "id": pc.id,
                "name": pc.full_name,
                "cluster": pc.cluster.value,
                "das": len([d for d in pc.das if d.is_enabled and not d.is_deleted]),
                "villages": sum(
                    len([v for v in d.villages if v.is_enabled and not v.is_deleted])
                    for d in pc.das if d.is_enabled and not d.is_deleted
                ),
                "url": f"/directory/pc/{pc.id}",
            }
            for pc in pcs
        ],
        "plans": _plan_rows(plans),
    }
