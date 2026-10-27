from __future__ import annotations

import json
import secrets
from collections.abc import Iterable
from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from flask import current_app
from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Font, PatternFill, Protection
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import (
    DA,
    ActionPlan,
    ActionPlanType,
    AuditAction,
    Committee,
    User,
    Village,
)
from ..scoping import can_manage_action_plan, require_scoped, scoped_select
from ..timeutils import current_month, local_today
from .audit import model_snapshot, record_audit

TEMPLATE_VERSION = "2.0"
STAGE_TTL_MINUTES = 30
EXPORT_SHEET = "Action Plans"
META_SHEET = "__META__"
PLAN_TYPES = (ActionPlanType.ATTENDANCE.value,)
SYSTEM_HEADERS = (
    "Plan ID",
    "Month",
    "Committee ID",
    "DA",
    "Village",
    "Committee",
    "Status",
)
EDITABLE_HEADERS = ("Type", "Assigned Date", "Notes")
ALL_HEADERS = (
    "Plan ID",
    "Month",
    "Committee ID",
    "DA",
    "Village",
    "Committee",
    "Type",
    "Assigned Date",
    "Notes",
    "Status",
)


class PlanningError(ValueError):
    pass


@dataclass(slots=True)
class ImportRow:
    excel_row: int
    committee_id: int | None
    plan_id: int | None
    plan_type: ActionPlanType | None
    assigned_date: date | None
    notes: str | None
    action: str
    errors: list[str]
    da_name: str = ""
    village_name: str = ""
    committee_name: str = ""


def month_start(value: str | date | None = None) -> date:
    if isinstance(value, date):
        return value.replace(day=1)

    raw = str(value or "").strip()

    if not raw:
        return current_month()

    try:
        if len(raw) == 7:
            return date.fromisoformat(f"{raw}-01")

        return date.fromisoformat(raw).replace(day=1)

    except ValueError as exc:
        raise PlanningError(
            "Month must use YYYY-MM format."
        ) from exc


def month_key(value: date) -> str:
    return value.strftime("%Y-%m")


def month_label(value: date) -> str:
    return value.strftime("%B %Y")


def add_months(value: date, months: int) -> date:
    index = value.year * 12 + (value.month - 1) + months

    return date(
        index // 12,
        index % 12 + 1,
        1,
    )


def _carried_date(previous: date | None, target_month: date) -> date | None:
    """Carry the scheduled *day* across months (clamped e.g. 31 -> 28)."""
    if previous is None:
        return None
    last_day = monthrange(target_month.year, target_month.month)[1]
    return date(target_month.year, target_month.month, min(previous.day, last_day))


def _recurrence_anchor(plan: ActionPlan) -> date | None:
    """Retain the last explicit scheduled day across short months.

    Automatically prepared records can be clamped in February; carry the
    original January 31 anchor into March rather than permanently using 28.
    Any human-edited/imported plan is the new recurrence anchor.
    """
    visited: set[int] = set()
    current = plan
    while current.prepared_from_id and current.assigned_by_user_id is None:
        if current.id in visited:
            break
        visited.add(current.id)
        source = db.session.get(ActionPlan, current.prepared_from_id)
        if source is None or not source.assigned_date:
            break
        current = source
    return current.assigned_date or plan.assigned_date


def ensure_recurring_attendance(user: User, target_month: date) -> int:
    """Fill *missing* current/future monthly slots from the last real assignment.

    Never replace any existing slot, including a deliberately blank draft or
    imported/monthly manual override. Older completed plans remain immutable.
    Idempotent across DA/PC/Admin reads via the unique committee/month key.
    A committee with no past scheduled date remains a PC setup task.
    """
    if target_month < current_month():
        return 0
    slots = _monthly_plan_slots(user, target_month)
    created = 0
    for committee in visible_committees(user):
        slot = slots.get(committee.id)
        if slot is not None and not (
            slot.prepared_from_id is not None
            and (slot.assigned_by_user_id is None or (slot.assigned_date is None and slot.plan_type is None))
            and slot.attendance_entry is None and slot.specials_entry is None
        ):
            continue  # Imported/manual/previously submitted monthly plans win.
        last = db.session.scalar(
            db.select(ActionPlan).where(
                ActionPlan.committee_id == committee.id,
                ActionPlan.plan_month.is_not(None),
                ActionPlan.plan_month < target_month,
                ActionPlan.assigned_date.is_not(None),
                ActionPlan.is_deleted.is_(False),
                ActionPlan.is_enabled.is_(True),
            ).order_by(ActionPlan.plan_month.desc()).limit(1)
        )
        if last is None:
            continue  # No date to infer. Do not invent the first PC schedule.
        if slot is not None:
            # A future system-generated row follows later manual changes in the
            # source month, but no human-created or imported slot is overwritten.
            slot.description = last.description
            slot.plan_type = ActionPlanType.ATTENDANCE
            slot.assigned_date = _carried_date(_recurrence_anchor(last), target_month)
            slot.prepared_from_id = last.id
            slot.notes = last.notes
            continue
        plan = ActionPlan(
            committee_id=committee.id, title=committee.name,
            description=last.description, plan_month=target_month,
            plan_type=ActionPlanType.ATTENDANCE,
            assigned_date=_carried_date(_recurrence_anchor(last), target_month),
            assigned_by_user_id=None, prepared_from_id=last.id,
            notes=last.notes,
        )
        db.session.add(plan)
        created += 1
    if created or db.session.dirty:
        try:
            db.session.commit()
        except IntegrityError:
            # Concurrent first visits may prepare the same slots; the request can
            # safely reload plans committed by another worker.
            db.session.rollback()
            return 0
    return created



def fill_blank_village_schedules(source: ActionPlan, user: User) -> list[int]:
    """Share a village's newly assigned day with its unscheduled committees.

    A single schedule entry is enough for that village. Explicitly dated,
    archived and locked plans are never overwritten, and all changes are
    audited in the same transaction as the source edit. Does not commit.
    """
    if not source.assigned_date or source.plan_type != ActionPlanType.ATTENDANCE:
        return []
    village_id = source.committee.village_id
    if not can_manage_action_plan(user, source.committee):
        raise PlanningError("You cannot schedule this village.")
    siblings = list(db.session.scalars(
        db.select(Committee).where(
            Committee.village_id == village_id,
            Committee.is_enabled.is_(True),
            Committee.is_deleted.is_(False),
        ).order_by(Committee.id)
    ))
    slot_rows = list(db.session.scalars(
        db.select(ActionPlan).join(Committee, ActionPlan.committee_id == Committee.id)
        .where(Committee.village_id == village_id, ActionPlan.plan_month == source.plan_month)
        .options(selectinload(ActionPlan.attendance_entry), selectinload(ActionPlan.specials_entry))
    ))
    slots = {row.committee_id: row for row in slot_rows}
    changed: list[int] = []
    for committee in siblings:
        if committee.id == source.committee_id or not can_manage_action_plan(user, committee):
            continue
        plan = slots.get(committee.id)
        if plan is not None:
            if plan.is_deleted or not plan.is_enabled or plan_locked(plan):
                continue
            # An explicit different date is intentional; preserve it.
            if plan.assigned_date is not None or plan.plan_type not in (None, ActionPlanType.ATTENDANCE):
                continue
            before = model_snapshot(plan)
            plan.plan_type = ActionPlanType.ATTENDANCE
            plan.assigned_date = source.assigned_date
            plan.assigned_by_user_id = user.id
            record_audit(AuditAction.UPDATE, plan, before=before,
                         after=model_snapshot(plan), actor=user)
        else:
            plan = ActionPlan(
                committee_id=committee.id, title=committee.name,
                plan_month=source.plan_month, plan_type=ActionPlanType.ATTENDANCE,
                assigned_date=source.assigned_date, assigned_by_user_id=user.id,
            )
            db.session.add(plan)
            db.session.flush()
            record_audit(AuditAction.CREATE, plan, after=model_snapshot(plan), actor=user)
        changed.append(committee.id)
    return changed


def action_plan_status(
    plan: ActionPlan,
    today: date | None = None,
) -> str:
    today = today or local_today()

    if not plan.is_executable:
        return "Draft"

    if (
        plan.attendance_entry
        and not plan.attendance_entry.is_deleted
    ):
        return plan.attendance_entry.status.value

    if (
        plan.specials_entry
        and not plan.specials_entry.is_deleted
    ):
        return (
            plan.specials_entry.status.value
            if plan.specials_entry.status
            else "Completed"
        )

    if plan.assigned_date and plan.assigned_date < today:
        return "Failure"

    if plan.assigned_date == today:
        return "Due today"

    return "Scheduled"


def plan_locked(
    plan: ActionPlan,
    today: date | None = None,
) -> bool:
    """Monthly history is immutable once completed or its month has passed."""

    today = today or local_today()
    current = today.replace(day=1)

    if (
        plan.attendance_entry
        and not plan.attendance_entry.is_deleted
    ):
        return True

    if (
        plan.specials_entry
        and not plan.specials_entry.is_deleted
    ):
        return True

    if (
        plan.assigned_date
        and plan.assigned_date < today
    ):
        return True

    return bool(
        plan.plan_month
        and plan.plan_month < current
    )


def _committee_query(user: User):
    return (
        scoped_select(Committee, user)
        .options(
            selectinload(Committee.village)
            .selectinload(Village.da)
            .selectinload(DA.pc)
        )
        .order_by(Committee.name)
    )


def visible_committees(
    user: User,
) -> list[Committee]:
    rows = list(
        db.session.scalars(
            _committee_query(user)
        ).unique()
    )

    return sorted(
        rows,
        key=lambda committee: (
            committee.village.da.full_name.casefold(),
            committee.village.name.casefold(),
            committee.name.casefold(),
        ),
    )


def monthly_plans(
    user: User,
    month: date,
) -> dict[int, ActionPlan]:
    stmt = (
        scoped_select(ActionPlan, user)
        .where(
            ActionPlan.plan_month == month
        )
        .options(
            selectinload(ActionPlan.committee)
            .selectinload(Committee.village)
            .selectinload(Village.da)
            .selectinload(DA.pc),
            selectinload(
                ActionPlan.attendance_entry
            ),
            selectinload(
                ActionPlan.specials_entry
            ),
        )
    )

    return {
        plan.committee_id: plan
        for plan in db.session.scalars(
            stmt
        ).unique()
    }


def _monthly_plan_slots(
    user: User,
    month: date,
) -> dict[int, ActionPlan]:
    """Return every scoped committee/month row, including archived lifecycle rows.

    The database uniqueness constraint covers soft-deleted ActionPlan rows too.
    Import and month preparation therefore need a lifecycle-inclusive lookup so
    they never attempt a second physical row for the same committee/month.
    """

    stmt = (
        scoped_select(
            ActionPlan,
            user,
            include_deleted=True,
            include_disabled=True,
        )
        .where(
            ActionPlan.plan_month == month
        )
        .options(
            selectinload(ActionPlan.committee)
            .selectinload(Committee.village)
            .selectinload(Village.da)
            .selectinload(DA.pc),
            selectinload(
                ActionPlan.attendance_entry
            ),
            selectinload(
                ActionPlan.specials_entry
            ),
        )
    )

    return {
        plan.committee_id: plan
        for plan in db.session.scalars(
            stmt
        ).unique()
    }


def _plan_has_any_field_history(
    plan: ActionPlan,
) -> bool:
    """Return True even when a linked field row is itself soft-deleted."""

    return (
        plan.attendance_entry is not None
        or plan.specials_entry is not None
    )


def planning_rows(
    user: User,
    month: date,
) -> list[dict[str, Any]]:
    plans = monthly_plans(
        user,
        month,
    )

    rows: list[dict[str, Any]] = []

    for committee in visible_committees(
        user
    ):
        plan = plans.get(
            committee.id
        )

        village = committee.village
        da = village.da

        rows.append(
            {
                "plan_id": (
                    plan.id
                    if plan
                    else None
                ),
                "month": month_key(
                    month
                ),
                "committee_id": (
                    committee.id
                ),
                "da_id": da.id,
                "da_name": da.full_name,
                "village_id": village.id,
                "village_name": village.name,
                "committee_name": (
                    committee.name
                ),
                "plan_type": (
                    plan.plan_type.value
                    if plan
                    and plan.plan_type
                    else None
                ),
                "assigned_date": (
                    plan.assigned_date.isoformat()
                    if plan
                    and plan.assigned_date
                    else None
                ),
                "notes": (
                    plan.notes
                    if plan
                    else None
                ),
                "status": (
                    action_plan_status(plan)
                    if plan
                    else "Draft"
                ),
                "locked": (
                    plan_locked(plan)
                    if plan
                    else False
                ),
                "entry_id": (
                    plan.attendance_entry.id
                    if (
                        plan
                        and plan.attendance_entry
                        and not plan.attendance_entry.is_deleted
                    )
                    else plan.specials_entry.id
                    if (
                        plan
                        and plan.specials_entry
                        and not plan.specials_entry.is_deleted
                    )
                    else None
                ),
            }
        )

    return rows


def planning_summary(
    rows: Iterable[dict[str, Any]],
) -> dict[str, int]:
    result = {
        "total": 0,
        "draft": 0,
        "scheduled": 0,
        "due_today": 0,
        "early": 0,
        "on_time": 0,
        "postponed": 0,
        "failure": 0,
    }

    for row in rows:
        result["total"] += 1

        key = {
            "Draft": "draft",
            "Scheduled": "scheduled",
            "Due today": "due_today",
            "Early": "early",
            "On-time": "on_time",
            "Postponed": "postponed",
            "Failure": "failure",
        }.get(
            row["status"]
        )

        if key:
            result[key] += 1

    return result


def da_work_queue(
    user: User,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """One DA work card per village, covering its incomplete monthly committees."""

    today = today or local_today()

    current_month_start = (
        today.replace(day=1)
    )

    next_month_start = add_months(
        current_month_start,
        1,
    )

    stmt = (
        scoped_select(
            ActionPlan,
            user,
        )
        .where(
            ActionPlan.plan_type == ActionPlanType.ATTENDANCE,
            ActionPlan.plan_month == current_month_start,
            ActionPlan.assigned_date.is_not(None),
        )
        .options(
            selectinload(
                ActionPlan.committee
            )
            .selectinload(
                Committee.village
            )
            .selectinload(
                Village.da
            )
            .selectinload(
                DA.pc
            ),
            selectinload(
                ActionPlan.attendance_entry
            ),
            selectinload(
                ActionPlan.specials_entry
            ),
        )
        .order_by(
            ActionPlan.assigned_date,
            ActionPlan.id,
        )
    )

    plans = list(
        db.session.scalars(
            stmt
        ).unique()
    )

    result: dict[
        str,
        list[dict[str, Any]],
    ] = {
        "today": [],
        "pending": [],
        "upcoming": [],
    }

    for plan in plans:
        if (
            plan.plan_type is None
            or plan.assigned_date is None
        ):
            continue

        attendance_complete = (
            plan.attendance_entry
            is not None
            and not plan.attendance_entry.is_deleted
        )

        specials_complete = (
            plan.specials_entry
            is not None
            and not plan.specials_entry.is_deleted
        )

        if (
            attendance_complete
            or specials_complete
        ):
            continue

        assigned_date = (
            plan.assigned_date
        )

        if assigned_date == today:
            bucket = "today"

        elif assigned_date < today:
            bucket = "pending"

        elif (
            current_month_start
            <= assigned_date
            < next_month_start
        ):
            bucket = "upcoming"

        else:
            # Future months are not part of the
            # DA's immediate work queue.
            continue

        village = (
            plan.committee.village
        )

        path = "/field/attendance"

        item: dict[str, Any] = {
            "plan_id": plan.id,
            "plan_month": (
                plan.plan_month.isoformat()
                if plan.plan_month
                else None
            ),
            "village_id": village.id,
            "village_name": (
                village.name
            ),
            "committee_id": (
                plan.committee_id
            ),
            "committee_name": (
                plan.committee.name
            ),
            "plan_type": (
                plan.plan_type.value
            ),
            "assigned_date": (
                assigned_date.isoformat()
            ),
            "notes": plan.notes,
            "go_url": (
                f"{path}?village={village.id}"
            ),
        }

        if bucket == "pending":
            item["days_overdue"] = (
                today
                - assigned_date
            ).days

        result[bucket].append(
            item
        )

    # Group all pending/current/upcoming committees of a village under one GO.
    # A mixed schedule shows just one village card in the highest-priority bucket.
    groups: dict[int, list[tuple[str, dict[str, Any]]]] = {}
    for category, items in result.items():
        for item in items:
            groups.setdefault(item["village_id"], []).append((category, item))
    result = {"today": [], "pending": [], "upcoming": []}
    for village_items in groups.values():
        order = {"today": 0, "pending": 1, "upcoming": 2}
        category, representative = min(village_items, key=lambda pair: (
            order[pair[0]], pair[1]["assigned_date"]
        ))
        card = dict(representative)
        card["committee_count"] = len(village_items)
        card["committee_name"] = f"{len(village_items)} committees · one visit"
        card["plan_type"] = "Attendance"
        result[category].append(card)

    for bucket in result.values():
        bucket.sort(
            key=lambda item: (
                item["assigned_date"],
                item["village_name"].casefold(),
                item[
                    "committee_name"
                ].casefold(),
                item["plan_id"],
            )
        )

    return {
        **result,
        "counts": {
            "today": len(
                result["today"]
            ),
            "pending": len(
                result["pending"]
            ),
            "upcoming": len(
                result["upcoming"]
            ),
        },
    }


def _cell_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    text = str(
        value
    ).strip()

    return text or None


def _parse_type(
    value: Any,
) -> ActionPlanType | None:
    raw = _cell_text(
        value
    )

    if raw is None:
        return None

    if raw.casefold() == "attendance":
        return ActionPlanType.ATTENDANCE
    raise PlanningError("Only Attendance is supported in new action plans.")


def _parse_excel_date(
    value: Any,
) -> date | None:
    if value in (
        None,
        "",
    ):
        return None

    if isinstance(
        value,
        datetime,
    ):
        return value.date()

    if isinstance(
        value,
        date,
    ):
        return value

    raw = str(
        value
    ).strip()

    for candidate in (
        raw,
        raw.replace(
            "/",
            "-",
        ),
    ):
        for fmt in (
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d-%m-%y",
        ):
            try:
                return datetime.strptime(
                    candidate,
                    fmt,
                ).date()

            except ValueError:
                pass

    raise PlanningError(
        "Assigned Date must be a valid date."
    )


def _headers(
    ws,
) -> dict[str, int]:
    result = {}

    for index, cell in enumerate(
        ws[1],
        1,
    ):
        label = _cell_text(
            cell.value
        )

        if label:
            result[label] = index

    missing = [
        header
        for header in ALL_HEADERS
        if header not in result
    ]

    if missing:
        raise PlanningError(
            "Workbook is missing columns: "
            + ", ".join(missing)
        )

    return result


def _export_styles(
    ws,
    row_count: int,
) -> None:
    navy = "1F4E5F"
    white = "FFFFFF"
    system = "E8E7E1"
    required = "FFF2CC"
    editable = "FFFFFF"
    locked_font = "555555"

    for cell in ws[1]:
        cell.fill = PatternFill(
            "solid",
            fgColor=navy,
        )

        cell.font = Font(
            color=white,
            bold=True,
        )

        cell.protection = Protection(
            locked=True
        )

    headers = {
        cell.value: cell.column
        for cell in ws[1]
    }

    for name in SYSTEM_HEADERS:
        col = headers[name]

        for row in range(
            2,
            row_count + 2,
        ):
            cell = ws.cell(
                row,
                col,
            )

            cell.fill = PatternFill(
                "solid",
                fgColor=system,
            )

            cell.font = Font(
                color=locked_font
            )

            cell.protection = (
                Protection(
                    locked=True
                )
            )

    for name in (
        "Type",
        "Assigned Date",
    ):
        col = headers[name]

        for row in range(
            2,
            row_count + 2,
        ):
            cell = ws.cell(
                row,
                col,
            )

            cell.fill = PatternFill(
                "solid",
                fgColor=required,
            )

            cell.protection = (
                Protection(
                    locked=False
                )
            )

    notes_col = headers[
        "Notes"
    ]

    for row in range(
        2,
        row_count + 2,
    ):
        ws.cell(
            row,
            notes_col,
        ).fill = PatternFill(
            "solid",
            fgColor=editable,
        )

        ws.cell(
            row,
            notes_col,
        ).protection = Protection(
            locked=False
        )

    type_col = get_column_letter(
        headers["Type"]
    )

    validation = DataValidation(
        type="list",
        formula1='"Attendance"',
        allow_blank=True,
        error=(
            "Choose Attendance."
        ),
        errorTitle=(
            "Invalid action-plan type"
        ),
    )

    ws.add_data_validation(
        validation
    )

    validation.add(
        f"{type_col}2:"
        f"{type_col}{row_count + 1}"
    )

    assigned_col = (
        get_column_letter(
            headers[
                "Assigned Date"
            ]
        )
    )

    type_col_letter = (
        get_column_letter(
            headers["Type"]
        )
    )

    yellow = PatternFill(
        "solid",
        fgColor="FFF2CC",
    )

    ws.conditional_formatting.add(
        (
            f"{assigned_col}2:"
            f"{assigned_col}"
            f"{row_count + 1}"
        ),
        FormulaRule(
            formula=[
                (
                    f'AND('
                    f'${type_col_letter}2<>'
                    f'"",'
                    f'${assigned_col}2=""'
                    f')'
                )
            ],
            fill=yellow,
        ),
    )

    ws.cell(1, headers["Assigned Date"]).comment = Comment(
        "Enter a date for one committee in the village. During import preview, "
        "other blank committee dates in that village are filled automatically. "
        "Already assigned dates are preserved.",
        "Bala Vikasa",
    )

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = (
        ws.dimensions
    )
    ws.sheet_view.showGridLines = (
        False
    )

    ws.protection.sheet = True
    ws.protection.enable()

    # No password: protection is guidance.
    # Server-side validation is the security boundary.
    widths = {
        "Plan ID": 13,
        "Month": 13,
        "Committee ID": 14,
        "DA": 22,
        "Village": 24,
        "Committee": 30,
        "Type": 16,
        "Assigned Date": 18,
        "Notes": 38,
        "Status": 16,
    }

    for name, width in widths.items():
        ws.column_dimensions[
            get_column_letter(
                headers[name]
            )
        ].width = width


def build_export_workbook(
    user: User,
    month: date,
) -> Workbook:
    rows = planning_rows(
        user,
        month,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = EXPORT_SHEET

    ws.append(
        ALL_HEADERS
    )

    for row in rows:
        ws.append(
            [
                row["plan_id"],
                row["month"],
                row[
                    "committee_id"
                ],
                row["da_name"],
                row["village_name"],
                row[
                    "committee_name"
                ],
                row["plan_type"],
                row["assigned_date"],
                row["notes"],
                row["status"],
            ]
        )

    _export_styles(
        ws,
        len(rows),
    )

    # Immutable rows are grey/locked even
    # in the editable columns.
    headers = {
        cell.value: cell.column
        for cell in ws[1]
    }

    for excel_row, row in enumerate(
        rows,
        2,
    ):
        if not row["locked"]:
            continue

        for name in EDITABLE_HEADERS:
            cell = ws.cell(
                excel_row,
                headers[name],
            )

            cell.fill = PatternFill(
                "solid",
                fgColor="E8E7E1",
            )

            cell.font = Font(
                color="555555"
            )

            cell.protection = (
                Protection(
                    locked=True
                )
            )

    meta = wb.create_sheet(
        META_SHEET
    )

    meta.sheet_state = "hidden"

    for key, value in (
        (
            "template_version",
            TEMPLATE_VERSION,
        ),
        (
            "month",
            month_key(month),
        ),
        (
            "exported_for_user_id",
            user.id,
        ),
        (
            "exported_for_role",
            user.role.value,
        ),
        (
            "exported_at_utc",
            datetime.now(
                UTC
            ).isoformat(),
        ),
    ):
        meta.append(
            [
                key,
                value,
            ]
        )

    return wb


def _validate_meta(
    wb,
    user: User,
    selected_month: date,
) -> None:
    if META_SHEET not in wb.sheetnames:
        raise PlanningError(
            "This is not a Model Village "
            "action-plan export workbook."
        )

    meta = {
        _cell_text(
            row[0].value
        ): _cell_text(
            row[1].value
        )
        for row in wb[
            META_SHEET
        ].iter_rows(
            min_row=1,
            max_col=2,
        )
        if _cell_text(
            row[0].value
        )
    }

    if (
        meta.get(
            "template_version"
        )
        != TEMPLATE_VERSION
    ):
        raise PlanningError(
            "Unsupported action-plan "
            "template version."
        )

    if (
        meta.get("month")
        != month_key(
            selected_month
        )
    ):
        raise PlanningError(
            f"Workbook month is "
            f"{meta.get('month') or 'unknown'}, "
            f"not {month_key(selected_month)}."
        )

    if (
        meta.get(
            "exported_for_user_id"
        )
        != str(user.id)
    ):
        raise PlanningError(
            "This workbook was exported for "
            "a different login. Export a fresh "
            "sheet from your own Action Plans page."
        )


def preview_import(
    path: Path,
    user: User,
    selected_month: date,
) -> dict[str, Any]:
    if (
        selected_month
        < current_month()
    ):
        raise PlanningError(
            "Past monthly history is immutable "
            "and cannot be imported."
        )

    try:
        wb = load_workbook(
            path,
            data_only=False,
        )

    except Exception as exc:
        raise PlanningError(
            "The uploaded file is not "
            "a readable .xlsx workbook."
        ) from exc

    _validate_meta(
        wb,
        user,
        selected_month,
    )

    if (
        EXPORT_SHEET
        not in wb.sheetnames
    ):
        raise PlanningError(
            f"Workbook must contain a "
            f"'{EXPORT_SHEET}' sheet."
        )

    ws = wb[EXPORT_SHEET]

    headers = _headers(
        ws
    )

    visible = {
        committee.id: committee
        for committee
        in visible_committees(
            user
        )
    }

    existing = monthly_plans(
        user,
        selected_month,
    )

    slots = _monthly_plan_slots(
        user,
        selected_month,
    )

    seen: set[int] = set()
    parsed: list[ImportRow] = []

    for excel_row in range(
        2,
        ws.max_row + 1,
    ):
        raw_committee = ws.cell(
            excel_row,
            headers[
                "Committee ID"
            ],
        ).value

        if raw_committee in (
            None,
            "",
        ):
            # Allow blank trailing/note rows only
            # if the row contains no editable data.
            if not any(
                ws.cell(
                    excel_row,
                    headers[name],
                ).value
                not in (
                    None,
                    "",
                )
                for name
                in EDITABLE_HEADERS
            ):
                continue

        errors: list[str] = []
        committee_id = None

        try:
            committee_id = int(
                raw_committee
            )

        except (
            TypeError,
            ValueError,
        ):
            errors.append(
                "Committee ID is missing or invalid."
            )

        committee = (
            visible.get(
                committee_id
            )
            if committee_id
            else None
        )

        if (
            committee_id
            and not committee
        ):
            errors.append(
                "Committee is outside your "
                "permitted scope or does not exist."
            )

        if (
            committee_id
            in seen
        ):
            errors.append(
                "Committee appears more than "
                "once in this workbook."
            )

        if committee_id:
            seen.add(
                committee_id
            )

        workbook_month = _cell_text(
            ws.cell(
                excel_row,
                headers["Month"],
            ).value
        )

        if (
            workbook_month
            != month_key(
                selected_month
            )
        ):
            errors.append(
                f"Month must remain "
                f"{month_key(selected_month)}."
            )

        try:
            plan_type = _parse_type(
                ws.cell(
                    excel_row,
                    headers["Type"],
                ).value
            )

        except PlanningError as exc:
            plan_type = None
            errors.append(
                str(exc)
            )

        try:
            assigned = (
                _parse_excel_date(
                    ws.cell(
                        excel_row,
                        headers[
                            "Assigned Date"
                        ],
                    ).value
                )
            )

        except PlanningError as exc:
            assigned = None
            errors.append(
                str(exc)
            )

        if assigned is not None and plan_type is None:
            # A date in any row is enough: Attendance is the only new
            # activity type, and sibling dates are inferred below.
            plan_type = ActionPlanType.ATTENDANCE

        if assigned and (
            assigned.year
            != selected_month.year
            or assigned.month
            != selected_month.month
        ):
            errors.append(
                f"Assigned Date must be inside "
                f"{month_label(selected_month)}."
            )

        notes = _cell_text(
            ws.cell(
                excel_row,
                headers["Notes"],
            ).value
        )

        plan = (
            existing.get(
                committee_id
            )
            if committee_id
            else None
        )

        archived_slot = (
            slots.get(
                committee_id
            )
            if (
                committee_id
                and plan is None
            )
            else None
        )

        if (
            archived_slot
            is not None
        ):
            if _plan_has_any_field_history(
                archived_slot
            ):
                errors.append(
                    "An archived monthly plan with "
                    "field history already exists. "
                    "Restore it from Recycle Bin "
                    "instead of importing a replacement."
                )

            elif plan_locked(
                archived_slot
            ):
                errors.append(
                    "An archived monthly plan occupies "
                    "this committee/month and is locked. "
                    "Restore or resolve it before importing."
                )

        plan_id_raw = ws.cell(
            excel_row,
            headers["Plan ID"],
        ).value

        try:
            workbook_plan_id = (
                int(plan_id_raw)
                if plan_id_raw
                not in (
                    None,
                    "",
                )
                else None
            )

        except (
            TypeError,
            ValueError,
        ):
            workbook_plan_id = None
            errors.append(
                "Plan ID was modified "
                "and is invalid."
            )

        if (
            plan
            and workbook_plan_id
            not in (
                None,
                plan.id,
            )
        ):
            errors.append(
                "Plan ID does not match "
                "the database record."
            )

        if (
            not plan
            and workbook_plan_id
            is not None
        ):
            errors.append(
                "Plan ID refers to a plan "
                "that does not exist for this month."
            )

        if (
            plan
            and plan_locked(plan)
        ):
            changed = (
                plan.plan_type
                != plan_type
                or plan.assigned_date
                != assigned
                or (
                    plan.notes
                    or None
                )
                != notes
            )

            if changed:
                errors.append(
                    "This monthly plan is locked "
                    "by immutable history and "
                    "cannot be changed."
                )

        if errors:
            action = "Error"

        elif plan is None:
            action = (
                "New"
                if (
                    plan_type
                    or assigned
                    or notes
                )
                else "Unchanged"
            )

        else:
            changed = (
                plan.plan_type
                != plan_type
                or plan.assigned_date
                != assigned
                or (
                    plan.notes
                    or None
                )
                != notes
            )

            action = (
                "Changed"
                if changed
                else "Unchanged"
            )

        parsed.append(
            ImportRow(
                excel_row=excel_row,
                committee_id=committee_id,
                plan_id=(
                    plan.id
                    if plan
                    else None
                ),
                plan_type=plan_type,
                assigned_date=assigned,
                notes=notes,
                action=action,
                errors=errors,
                da_name=(
                    committee.village.da.full_name
                    if committee
                    else ""
                ),
                village_name=(
                    committee.village.name
                    if committee
                    else ""
                ),
                committee_name=(
                    committee.name
                    if committee
                    else ""
                ),
            )
        )

    # A PC enters one date per village in Excel. Fill *only* blank rows
    # belonging to that village. Explicit dates always win. If a village
    # contains multiple explicit dates, blanks are ambiguous and must be set.
    village_dates: dict[int, set[date]] = {}
    for row in parsed:
        if row.committee_id in visible and row.assigned_date and not row.errors:
            vid = visible[row.committee_id].village_id
            village_dates.setdefault(vid, set()).add(row.assigned_date)
    for row in parsed:
        if row.errors or row.committee_id not in visible or row.assigned_date is not None:
            continue
        vid = visible[row.committee_id].village_id
        dates = village_dates.get(vid, set())
        if not dates:
            continue
        if len(dates) != 1:
            row.errors.append("Village has different scheduled dates; choose a date for this committee.")
            row.action = "Error"
            continue
        inherited_date = next(iter(dates))
        plan = existing.get(row.committee_id)
        if plan and plan_locked(plan) and (plan.assigned_date != inherited_date or plan.plan_type != ActionPlanType.ATTENDANCE):
            row.errors.append("This plan is locked and cannot inherit a village date.")
            row.action = "Error"
            continue
        row.assigned_date = inherited_date
        row.plan_type = ActionPlanType.ATTENDANCE
        if plan is None:
            row.action = "New"
        else:
            row.action = "Changed" if (plan.plan_type != row.plan_type or plan.assigned_date != row.assigned_date or (plan.notes or None) != row.notes) else "Unchanged"

    counts = {
        key: 0
        for key in (
            "New",
            "Changed",
            "Unchanged",
            "Error",
        )
    }

    for row in parsed:
        counts[
            row.action
        ] += 1

    return {
        "month": month_key(
            selected_month
        ),
        "month_label": (
            month_label(
                selected_month
            )
        ),
        "counts": counts,
        "has_errors": (
            counts["Error"] > 0
        ),
        "rows": [
            {
                "excel_row": (
                    row.excel_row
                ),
                "committee_id": (
                    row.committee_id
                ),
                "plan_id": (
                    row.plan_id
                ),
                "da_name": (
                    row.da_name
                ),
                "village_name": (
                    row.village_name
                ),
                "committee_name": (
                    row.committee_name
                ),
                "plan_type": (
                    row.plan_type.value
                    if row.plan_type
                    else None
                ),
                "assigned_date": (
                    row.assigned_date.isoformat()
                    if row.assigned_date
                    else None
                ),
                "notes": row.notes,
                "action": row.action,
                "errors": row.errors,
            }
            for row in parsed
        ],
    }


def _stage_root() -> Path:
    root = (
        Path(
            current_app.instance_path
        )
        / "import_staging"
        / "action-plans"
    )

    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    return root


def stage_import(
    source_path: Path,
    user: User,
    selected_month: date,
) -> tuple[
    str,
    dict[str, Any],
]:
    preview = preview_import(
        source_path,
        user,
        selected_month,
    )

    token = secrets.token_urlsafe(
        24
    )

    root = _stage_root()

    target = (
        root
        / f"{token}.xlsx"
    )

    target.write_bytes(
        source_path.read_bytes()
    )

    (
        root
        / f"{token}.json"
    ).write_text(
        json.dumps(
            {
                "user_id": user.id,
                "month": month_key(
                    selected_month
                ),
                "created_at": (
                    datetime.now(
                        UTC
                    ).isoformat()
                ),
            }
        ),
        encoding="utf-8",
    )

    return token, preview


def _staged_file(
    token: str,
    user: User,
    selected_month: date,
) -> Path:
    if (
        not token
        or any(
            ch
            not in (
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "abcdefghijklmnopqrstuvwxyz"
                "0123456789-_"
            )
            for ch in token
        )
    ):
        raise PlanningError(
            "Invalid import preview token."
        )

    root = _stage_root()

    meta_path = (
        root
        / f"{token}.json"
    )

    xlsx_path = (
        root
        / f"{token}.xlsx"
    )

    if (
        not meta_path.exists()
        or not xlsx_path.exists()
    ):
        raise PlanningError(
            "Import preview expired "
            "or was not found."
        )

    try:
        meta = json.loads(
            meta_path.read_text(
                encoding="utf-8"
            )
        )

    except Exception as exc:
        raise PlanningError(
            "Import preview metadata is invalid."
        ) from exc

    if (
        int(
            meta.get(
                "user_id",
                -1,
            )
        )
        != user.id
        or meta.get("month")
        != month_key(
            selected_month
        )
    ):
        raise PlanningError(
            "Import preview does not belong "
            "to this user/month."
        )

    try:
        created = datetime.fromisoformat(
            meta["created_at"]
        )

        if created.tzinfo is None:
            created = (
                created.replace(
                    tzinfo=UTC
                )
            )

    except Exception as exc:
        raise PlanningError(
            "Import preview metadata is invalid."
        ) from exc

    if (
        datetime.now(UTC)
        - created
        > timedelta(
            minutes=STAGE_TTL_MINUTES
        )
    ):
        meta_path.unlink(
            missing_ok=True
        )

        xlsx_path.unlink(
            missing_ok=True
        )

        raise PlanningError(
            "Import preview expired. "
            "Validate the workbook again."
        )

    return xlsx_path


def confirm_import(
    token: str,
    user: User,
    selected_month: date,
) -> dict[str, Any]:
    path = _staged_file(
        token,
        user,
        selected_month,
    )

    preview = preview_import(
        path,
        user,
        selected_month,
    )

    if preview["has_errors"]:
        raise PlanningError(
            "Import still contains validation "
            "errors; nothing was saved."
        )

    # Include archived rows because the DB uniqueness constraint
    # applies to them as well. A safe archived slot is restored
    # in place so its ActionPlan ID remains stable.
    existing = _monthly_plan_slots(
        user,
        selected_month,
    )

    created = 0
    updated = 0
    committed = False

    try:
        for row in preview[
            "rows"
        ]:
            if row["action"] not in {
                "New",
                "Changed",
            }:
                continue

            committee = require_scoped(
                Committee,
                int(
                    row[
                        "committee_id"
                    ]
                ),
                user,
            )

            if not can_manage_action_plan(
                user,
                committee,
            ):
                raise PlanningError(
                    "A row moved outside your "
                    "action-plan management scope."
                )

            plan = existing.get(
                committee.id
            )

            plan_type = (
                ActionPlanType(
                    row[
                        "plan_type"
                    ]
                )
                if row[
                    "plan_type"
                ]
                else None
            )

            assigned = (
                date.fromisoformat(
                    row[
                        "assigned_date"
                    ]
                )
                if row[
                    "assigned_date"
                ]
                else None
            )

            if plan is None:
                plan = ActionPlan(
                    committee_id=committee.id,
                    title=committee.name,
                    description=None,
                    plan_month=selected_month,
                    plan_type=plan_type,
                    assigned_date=assigned,
                    assigned_by_user_id=user.id,
                    notes=row["notes"],
                )

                db.session.add(
                    plan
                )

                try:
                    db.session.flush()

                except IntegrityError as exc:
                    raise PlanningError(
                        "Another action plan already "
                        "occupies this committee/month. "
                        "Validate the workbook again "
                        "before confirming."
                    ) from exc

                record_audit(
                    AuditAction.IMPORT,
                    plan,
                    after=model_snapshot(
                        plan
                    ),
                    actor=user,
                )

                existing[
                    committee.id
                ] = plan

                created += 1
                continue

            was_archived = bool(
                plan.is_deleted
                or not plan.is_enabled
            )

            if was_archived:
                # Never revive a plan that has any field-entry history,
                # even if the field row is also in Recycle Bin.
                if _plan_has_any_field_history(
                    plan
                ):
                    raise PlanningError(
                        "An archived action plan with "
                        "field history cannot be reused "
                        "by import. Restore it from "
                        "Recycle Bin instead."
                    )

                if plan_locked(
                    plan
                ):
                    raise PlanningError(
                        "An archived action plan for "
                        "this committee/month is locked "
                        "and cannot be reused."
                    )

            elif plan_locked(
                plan
            ):
                raise PlanningError(
                    "A monthly plan became locked "
                    "before import confirmation."
                )

            before = model_snapshot(
                plan
            )

            if was_archived:
                plan.is_deleted = False
                plan.deleted_at = None
                plan.is_enabled = True

            plan.title = (
                committee.name
            )

            plan.plan_type = (
                plan_type
            )

            plan.assigned_date = (
                assigned
            )

            plan.assigned_by_user_id = (
                user.id
            )

            plan.notes = (
                row["notes"]
            )

            record_audit(
                AuditAction.IMPORT,
                plan,
                before=before,
                after=model_snapshot(
                    plan
                ),
                actor=user,
            )

            if was_archived:
                created += 1
            else:
                updated += 1

        db.session.commit()
        committed = True

    except Exception:
        db.session.rollback()
        raise

    finally:
        # A DB failure should not consume the preview token.
        # Consume only after a successful commit so the operator
        # can correct the cause and retry.
        if committed:
            root = _stage_root()

            for suffix in (
                ".xlsx",
                ".json",
            ):
                candidate = (
                    root
                    / f"{token}{suffix}"
                )

                candidate.unlink(
                    missing_ok=True
                )

    return {
        "created": created,
        "updated": updated,
        "month": month_key(
            selected_month
        ),
    }


def prepare_next_month(
    user: User,
    source_month: date,
) -> dict[
    str,
    int | str,
]:
    target_month = add_months(
        source_month,
        1,
    )

    if (
        target_month
        < current_month()
    ):
        raise PlanningError(
            "Cannot prepare a month that "
            "is already in immutable history."
        )

    source = monthly_plans(
        user,
        source_month,
    )

    target = _monthly_plan_slots(
        user,
        target_month,
    )

    created = 0
    skipped = 0

    for committee in visible_committees(
        user
    ):
        if not can_manage_action_plan(
            user,
            committee,
        ):
            continue

        if committee.id in target:
            skipped += 1
            continue

        previous = source.get(
            committee.id
        )

        plan = ActionPlan(
            committee_id=committee.id,
            title=committee.name,
            description=(
                previous.description
                if previous
                else None
            ),
            plan_month=target_month,
            plan_type=(ActionPlanType.ATTENDANCE if previous and previous.assigned_date else None),
            assigned_date=_carried_date(_recurrence_anchor(previous), target_month) if previous else None,
            assigned_by_user_id=None,
            prepared_from_id=(
                previous.id
                if previous
                else None
            ),
            notes=(
                previous.notes
                if previous
                else None
            ),
        )

        db.session.add(
            plan
        )

        db.session.flush()

        record_audit(
            AuditAction.CREATE,
            plan,
            after=model_snapshot(
                plan
            ),
            actor=user,
        )

        created += 1

    db.session.commit()

    return {
        "created": created,
        "skipped": skipped,
        "source_month": month_key(
            source_month
        ),
        "target_month": month_key(
            target_month
        ),
    }