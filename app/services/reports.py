from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import (
    DA,
    ActionPlan,
    ActionPlanType,
    AttendanceEntry,
    Committee,
    CommitteeMember,
    SpecialsEntry,
    User,
    Village,
    VillageAttendanceVisit,
)
from ..reporting_core import ReportingPeriod
from ..scoping import inherited_cluster, scoped_select
from .monthly_plans import action_plan_status, month_key, month_label


def _month_bounds(month: date) -> tuple[date, date]:
    if month.month == 12:
        nxt = date(month.year + 1, 1, 1)
    else:
        nxt = date(month.year, month.month + 1, 1)
    return month, nxt


def report_plans(
    user: User,
    month: date,
    *,
    plan_type: str | None = None,
    status: str | None = None,
    village_id: int | None = None,
    period: ReportingPeriod | None = None,
) -> list[ActionPlan]:
    stmt = (
        scoped_select(ActionPlan, user)
        .where(
            ActionPlan.plan_type.is_not(None),
            ActionPlan.assigned_date.is_not(None),
        )
        .options(
            selectinload(ActionPlan.committee)
            .selectinload(Committee.village)
            .selectinload(Village.da)
            .selectinload(DA.pc),
            selectinload(ActionPlan.attendance_entry)
            .selectinload(AttendanceEntry.visited_members),
            selectinload(ActionPlan.specials_entry),
        )
        .order_by(ActionPlan.assigned_date.desc(), ActionPlan.id.desc())
    )
    if period is None:
        stmt = stmt.where(ActionPlan.plan_month == month)
    else:
        attendance_bounds = [AttendanceEntry.visit_date <= period.end, AttendanceEntry.is_enabled.is_(True), AttendanceEntry.is_deleted.is_(False)]
        special_bounds = [SpecialsEntry.event_date <= period.end, SpecialsEntry.is_enabled.is_(True), SpecialsEntry.is_deleted.is_(False)]
        if period.start:
            attendance_bounds.append(AttendanceEntry.visit_date >= period.start)
            special_bounds.append(SpecialsEntry.event_date >= period.start)
        stmt = stmt.where(or_(ActionPlan.attendance_entry.has(and_(*attendance_bounds)),
                              ActionPlan.specials_entry.has(and_(*special_bounds))))
    if village_id is not None:
        stmt = stmt.where(ActionPlan.committee.has(Committee.village_id == village_id))
    if plan_type:
        stmt = stmt.where(ActionPlan.plan_type == ActionPlanType(plan_type))
    plans = [p for p in db.session.scalars(stmt).unique()
             if p.committee.village.is_enabled and not p.committee.village.is_deleted]
    if status:
        plans = [plan for plan in plans if action_plan_status(plan) == status]
    return plans


def report_row(plan: ActionPlan) -> dict[str, Any]:
    village = plan.committee.village
    da = village.da
    entry = plan.attendance_entry if plan.plan_type == ActionPlanType.ATTENDANCE else plan.specials_entry
    activity_date = None
    if isinstance(entry, AttendanceEntry):
        activity_date = entry.visit_date
    elif isinstance(entry, SpecialsEntry):
        activity_date = entry.event_date
    return {
        "plan_id": plan.id,
        "date": (activity_date or plan.assigned_date).isoformat() if (activity_date or plan.assigned_date) else None,
        "assigned_date": plan.assigned_date.isoformat() if plan.assigned_date else None,
        "da": da.full_name,
        "village": village.name,
        "village_id": village.id,
        "committee": plan.committee.name,
        "type": plan.plan_type.value if plan.plan_type else "Draft",
        "status": action_plan_status(plan),
        "has_entry": bool(entry and not entry.is_deleted),
        "people_attended": entry.total_count if isinstance(entry, AttendanceEntry) and not entry.is_deleted else 0,
        "new_members": entry.new_members_count if isinstance(entry, AttendanceEntry) and not entry.is_deleted else 0,
        "male": entry.male_count if isinstance(entry, AttendanceEntry) and not entry.is_deleted else 0,
        "female": entry.female_count if isinstance(entry, AttendanceEntry) and not entry.is_deleted else 0,
        "history_kind": "Historical committee attendance",
        "view_url": f"/reports/plan/{plan.id}",
    }


def report_rows(user: User, month: date, *, plan_type: str | None = None, status: str | None = None, village_id: int | None = None, period: ReportingPeriod | None = None, q: str = ""):
    """Group new village visits into one visible report, retain legacy rows."""
    rows: list[dict[str, Any]] = []
    grouped: dict[int, list[ActionPlan]] = {}
    for plan in report_plans(user, month, plan_type=plan_type, status=None, village_id=village_id, period=period):
        entry = plan.attendance_entry
        if entry and (not entry.is_enabled or entry.is_deleted or
                      (entry.village_visit and (not entry.village_visit.is_enabled or entry.village_visit.is_deleted))):
            continue
        if plan.plan_type == ActionPlanType.ATTENDANCE and (entry is None or entry.is_deleted):
            continue  # Unexecuted legacy plans are not DA attendance reports.
        if entry and not entry.is_deleted and entry.village_visit_id is not None:
            grouped.setdefault(entry.village_visit_id, []).append(plan)
        else:
            rows.append(report_row(plan))
    for visit_id, plans in grouped.items():
        representative = report_row(plans[0])
        # A village visit appears once in the ledger: sum its underlying committee rows.
        parent_visit = plans[0].attendance_entry.village_visit
        if period and not period.contains(parent_visit.visit_date):
            continue
        attendance = [e for e in parent_visit.entries if e.is_enabled and not e.is_deleted]
        group_new_members = (
            parent_visit.new_members_count
            if parent_visit and parent_visit.visit_month
            else sum(e.new_members_count for e in attendance)
        )
        representative.update(
            date=parent_visit.visit_date.isoformat(),
            people_attended=sum(e.total_count for e in attendance),
            male=sum(e.male_count for e in attendance), female=sum(e.female_count for e in attendance),
            history_kind="Village submission",
            new_members=group_new_members,
            village_visit_id=visit_id,
            committee=f"{len(attendance)} committees · Village attendance",
            type="Attendance",
            view_url=f"/reports/village/{visit_id}",
            status=("Recorded" if parent_visit.visit_month is not None else "Postponed" if any(action_plan_status(p) == "Postponed" for p in plans)
                    else "Early" if any(action_plan_status(p) == "Early" for p in plans) else "On-time"),
        )
        rows.append(representative)
    # Newly submitted DA-led visits have no action-plan foreign key.
    start, end = ((period.start or date(2000, 1, 1), period.end + timedelta(days=1))
                  if period else _month_bounds(month))
    visits = db.session.scalars(
        scoped_select(VillageAttendanceVisit, user)
        .where(VillageAttendanceVisit.visit_date >= start,
               VillageAttendanceVisit.visit_date < end,
               VillageAttendanceVisit.is_enabled.is_(True),
               VillageAttendanceVisit.is_deleted.is_(False))
        .options(selectinload(VillageAttendanceVisit.village),
                 selectinload(VillageAttendanceVisit.entries))
    ).unique().all()
    existing_ids = {row.get("village_visit_id") for row in rows}
    if plan_type in (None, "Attendance"):
        for visit in visits:
            if not visit.village.is_enabled or visit.village.is_deleted:
                continue
            if village_id is not None and visit.village_id != village_id:
                continue
            if visit.id in existing_ids:
                continue
            entries = [e for e in visit.entries if e.is_enabled and not e.is_deleted]
            if not entries:
                continue
            submitter = db.session.get(User, visit.submitted_by_user_id)
            rows.append({
                "plan_id": None, "village_visit_id": visit.id,
                "date": visit.visit_date.isoformat(), "assigned_date": None,
                "da": submitter.display_name if submitter else visit.village.da.full_name,
                "village": visit.village.name, "village_id": visit.village_id,
                "committee": f"{len(entries)} committees · Village attendance",
                "type": "Attendance", "status": "Recorded", "has_entry": True,
                "male": sum(e.male_count for e in entries), "female": sum(e.female_count for e in entries),
                "history_kind": "Village submission",
                "people_attended": sum(e.total_count for e in entries),
                "new_members": visit.new_members_count if visit.visit_month else sum(e.new_members_count for e in entries),
                "view_url": f"/reports/village/{visit.id}",
            })
    if status:
        rows = [row for row in rows if row["status"] == status]
    if q.strip():
        search = q.strip().casefold()
        rows = [row for row in rows if search in " ".join(str(row.get(k) or "") for k in
                ("date", "da", "village", "committee", "type", "status")).casefold()]
    return sorted(rows, key=lambda row: row.get("date") or "", reverse=True)


def report_detail(plan: ActionPlan) -> dict[str, Any]:
    committee = plan.committee
    village = committee.village
    da = village.da
    pc = da.pc
    counts = dict(
        db.session.execute(
            db.select(CommitteeMember.gender, func.count(CommitteeMember.id))
            .where(
                CommitteeMember.committee_id == committee.id,
                CommitteeMember.is_enabled.is_(True),
                CommitteeMember.is_deleted.is_(False),
            )
            .group_by(CommitteeMember.gender)
        ).all()
    )
    detail: dict[str, Any] = {
        "plan_id": plan.id,
        "month": month_key(plan.plan_month) if plan.plan_month else None,
        "month_label": month_label(plan.plan_month) if plan.plan_month else None,
        "type": plan.plan_type.value if plan.plan_type else "Draft",
        "status": action_plan_status(plan),
        "assigned_date": plan.assigned_date.isoformat() if plan.assigned_date else None,
        "notes": plan.notes,
        "cluster": inherited_cluster(plan),
        "pc": pc.full_name,
        "da": da.full_name,
        "village": village.name,
        "mandal": village.mandal,
        "district": village.district,
        "committee": committee.name,
        "latitude": village.latitude,
        "longitude": village.longitude,
        "master": {
            "male": counts.get("Male", 0),
            "female": counts.get("Female", 0),
            "unknown": sum(value for key, value in counts.items() if key not in {"Male", "Female"}),
            "total": sum(counts.values()),
        },
        "entry": None,
    }
    if plan.attendance_entry and not plan.attendance_entry.is_deleted:
        entry = plan.attendance_entry
        grouped: dict[str, list[str]] = defaultdict(list)
        for selected in entry.visited_members:
            if selected.is_enabled and not selected.is_deleted:
                grouped[selected.designation_snapshot].append(selected.member_name_snapshot)
        detail["latitude"] = entry.latitude if entry.latitude is not None else detail["latitude"]
        detail["longitude"] = entry.longitude if entry.longitude is not None else detail["longitude"]
        detail["entry"] = {
            "id": entry.id,
            "date": entry.visit_date.isoformat(),
            "male": entry.male_count,
            "female": entry.female_count,
            "total": entry.total_count,
            "new_members": entry.new_members_count,
            "visit_members": dict(grouped),
            "reason": entry.reason,
            "remarks": entry.remarks,
            "photo_url": f"/api/v1/photos/attendance/{entry.id}" if entry.photo_path else None,
            "gps_source": entry.geolocation_source,
            "submitted_at": entry.submitted_at.isoformat(),
            "submitted_by": entry.submitted_by.display_name,
        }
    elif plan.specials_entry and not plan.specials_entry.is_deleted:
        entry = plan.specials_entry
        detail["latitude"] = entry.latitude if entry.latitude is not None else detail["latitude"]
        detail["longitude"] = entry.longitude if entry.longitude is not None else detail["longitude"]
        detail["entry"] = {
            "id": entry.id,
            "date": entry.event_date.isoformat(),
            "title": entry.title or committee.name,
            "participants": entry.participant_count,
            "scope": entry.scope.value,
            "reason": entry.reason,
            "notes": entry.notes,
            "photo_url": f"/api/v1/photos/specials/{entry.id}" if entry.photo_path else None,
            "gps_source": entry.geolocation_source,
            "submitted_at": entry.submitted_at.isoformat(),
            "submitted_by": entry.submitted_by.display_name,
        }
    return detail


def report_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    statuses = {"Recorded": 0, "Early": 0, "On-time": 0, "Postponed": 0}
    for row in rows:
        if row["status"] in statuses:
            statuses[row["status"]] += 1
    return {
        "total": len(rows),
        "people_attended": sum(int(row.get("people_attended") or 0) for row in rows),
        "new_members": sum(int(row.get("new_members") or 0) for row in rows),
        **statuses,
    }


def _village_visit_export_rows(visit: VillageAttendanceVisit, submitter_name: str) -> list[list[Any]]:
    """Preserve each committee/member without multiplying village-level totals.

    A row is emitted even for a committee with zero selected members. Attendance
    figures appear once per committee, and New Members appears once per village
    visit, so Excel SUM columns remain meaningful.
    """
    village = visit.village
    entries = sorted(
        (entry for entry in visit.entries
         if entry.is_enabled and not entry.is_deleted),
        key=lambda entry: (entry.committee.name.casefold(), entry.id),
    )
    new_members = (visit.new_members_count if visit.visit_month is not None
                   else sum(entry.new_members_count for entry in entries))
    rows: list[list[Any]] = []
    for committee_index, entry in enumerate(entries):
        members = [member for member in entry.visited_members
                   if member.is_enabled and not member.is_deleted]
        for member_index, member in enumerate(members or [None]):
            first_committee_row = member_index == 0
            first_village_row = committee_index == 0 and first_committee_row
            rows.append([
                month_key(visit.visit_date.replace(day=1)),
                visit.visit_date.isoformat(), None,
                village.da.pc.cluster.value, village.da.pc.full_name,
                submitter_name, village.name, entry.committee.name,
                "Attendance", "Recorded",
                entry.male_count if first_committee_row else None,
                entry.female_count if first_committee_row else None,
                entry.total_count if first_committee_row else None,
                new_members if first_village_row else None,
                member.member_name_snapshot if member else "",
                member.designation_snapshot if member else "",
                None, None, None,
                visit.remarks if first_village_row else None,
                visit.latitude, visit.longitude,
                f"/api/v1/photos/attendance/{entry.id}" if first_village_row else None,
            ])
    return rows


def export_report_workbook(user: User, month: date, *, plan_type: str | None = None, status: str | None = None, village_id: int | None = None, period: ReportingPeriod | None = None, q: str = "") -> Workbook:
    selected_rows = report_rows(user, month, plan_type=plan_type, status=status, village_id=village_id, period=period, q=q)
    selected_plans = {row.get('plan_id') for row in selected_rows if not row.get('village_visit_id')}
    selected_visits = {row.get('village_visit_id') for row in selected_rows if row.get('village_visit_id')}
    plans = [plan for plan in report_plans(user, month, plan_type=plan_type, status=None, village_id=village_id, period=period)
             if plan.plan_type != ActionPlanType.ATTENDANCE or
             (plan.attendance_entry is not None and not plan.attendance_entry.is_deleted)]
    wb = Workbook()
    ws = wb.active
    ws.title = "Reports"
    headers = [
        "Month", "Date", "Assigned Date", "Cluster", "PC", "DA", "Village", "Committee",
        "Type", "Status", "Male", "Female", "Total", "New Members",
        "Committee Member Name", "Visit Designation", "Participants", "Scope", "Reason",
        "Notes / Remarks", "Latitude", "Longitude", "Photo URL",
    ]
    ws.append(headers)
    for plan in plans:
        parent_id = plan.attendance_entry.village_visit_id if plan.attendance_entry else None
        if parent_id is not None or plan.id not in selected_plans:
            continue
        detail = report_detail(plan)
        entry = detail["entry"] or {}
        visit_members = entry.get("visit_members") or {}
        flattened = [
            (designation, name)
            for designation, names in visit_members.items()
            for name in names
        ] or [("", "")]
        for index, (designation, member_name) in enumerate(flattened):
            ws.append(
                [
                    detail["month"],
                    entry.get("date") if index == 0 else entry.get("date"),
                    detail["assigned_date"],
                    detail["cluster"],
                    detail["pc"],
                    detail["da"],
                    detail["village"],
                    detail["committee"],
                    detail["type"],
                    detail["status"],
                    entry.get("male") if index == 0 else None,
                    entry.get("female") if index == 0 else None,
                    entry.get("total") if index == 0 else None,
                    entry.get("new_members") if index == 0 else None,
                    member_name,
                    designation,
                    entry.get("participants"),
                    entry.get("scope"),
                    entry.get("reason"),
                    entry.get("remarks") or entry.get("notes") or detail["notes"],
                    detail["latitude"],
                    detail["longitude"],
                    entry.get("photo_url"),
                ]
            )

    navy = "1F4E5F"
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor=navy)
        cell.font = Font(color="FFFFFF", bold=True)
    # DA-led visits: export committee-wise attendance and recorded member names.
    # A village-wide New Members count is written exactly once per visit.
    start, end = ((period.start or date(2000, 1, 1), period.end + timedelta(days=1))
                  if period else _month_bounds(month))
    if plan_type in (None, "Attendance"):
        visits = db.session.scalars(scoped_select(VillageAttendanceVisit, user).where(
            VillageAttendanceVisit.visit_date >= start,
            VillageAttendanceVisit.visit_date < end,
            VillageAttendanceVisit.is_enabled.is_(True),
            VillageAttendanceVisit.is_deleted.is_(False),
        ).options(
            selectinload(VillageAttendanceVisit.village)
            .selectinload(Village.da).selectinload(DA.pc),
            selectinload(VillageAttendanceVisit.entries)
            .selectinload(AttendanceEntry.committee),
            selectinload(VillageAttendanceVisit.entries)
            .selectinload(AttendanceEntry.visited_members),
        )).unique().all()
        for visit in visits:
            if visit.id not in selected_visits:
                continue
            if village_id is not None and visit.village_id != village_id:
                continue
            submitter = db.session.get(User, visit.submitted_by_user_id)
            for row in _village_visit_export_rows(
                visit, submitter.display_name if submitter else "DA",
            ):
                ws.append(row)
    # Sanitize all exported text. Never let a user-supplied name become an Excel formula.
    from ..reporting_exports import safe_cell
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.value = safe_cell(cell.value)
    summary_sheet = wb.create_sheet("Selection summary")
    summary_sheet.append(["Metric", "Value"])
    summary_sheet.append(["Period", period.label if period else month_label(month)])
    summary_sheet.append(["Search", safe_cell(q)])
    for key, value in report_summary(selected_rows).items():
        summary_sheet.append([key, value])
    summary_sheet.column_dimensions['A'].width = 26
    summary_sheet.column_dimensions['B'].width = 60
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    ws.sheet_view.showGridLines = False
    widths = [12, 14, 16, 12, 22, 22, 24, 28, 14, 14, 10, 10, 10, 14, 26, 18, 14, 14, 28, 34, 14, 14, 28]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    return wb
