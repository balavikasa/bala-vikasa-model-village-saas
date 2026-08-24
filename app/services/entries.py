from __future__ import annotations

import json
import uuid
from datetime import date
from typing import Any

from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from werkzeug.datastructures import FileStorage

from ..extensions import db
from ..models import (
    ActionPlan,
    ActionPlanType,
    AttendanceEntry,
    AttendanceStatus,
    AttendanceVisitMember,
    AuditAction,
    Committee,
    CommitteeMember,
    Role,
    SpecialScope,
    SpecialsEntry,
    User,
    Village,
)
from ..scoping import ScopeError, can_submit_for_village, require_scoped
from ..timeutils import current_month
from .audit import model_snapshot, record_audit
from .files import delete_photo, save_photo


class EntryValidationError(ValueError):
    pass


VISIT_DESIGNATIONS = {"President", "Vice President", "Secretary", "Member"}


def _date(value: Any, field: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise EntryValidationError(f"{field} must be a valid ISO date.") from exc


def _integer(value: Any, field: str, *, minimum: int = 0) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise EntryValidationError(f"{field} must be a whole number.") from exc
    if result < minimum:
        raise EntryValidationError(f"{field} must be at least {minimum}.")
    return result


def _float_or_none(value: Any) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise EntryValidationError("Coordinates must be numeric.") from exc


def _member_ids(value: Any) -> list[int]:
    if value in (None, "", []):
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            value = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            value = [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, list):
        raise EntryValidationError("Selected committee members must be a list.")
    result: list[int] = []
    for item in value:
        try:
            member_id = int(item)
        except (TypeError, ValueError) as exc:
            raise EntryValidationError("Selected committee member contains an invalid ID.") from exc
        if member_id not in result:
            result.append(member_id)
    return result


def attendance_status(assigned_date: date, visit_date: date) -> AttendanceStatus:
    if visit_date < assigned_date:
        return AttendanceStatus.EARLY
    if visit_date == assigned_date:
        return AttendanceStatus.ON_TIME
    return AttendanceStatus.POSTPONED


def _submission_id(value: Any) -> str:
    candidate = str(value or "").strip() or str(uuid.uuid4())
    if len(candidate) > 80:
        raise EntryValidationError("client_submission_id is too long.")
    return candidate


def _resolve_chain(payload: dict[str, Any], user: User) -> tuple[Village, Committee]:
    village_id = _integer(payload.get("village_id"), "village_id", minimum=1)
    village = require_scoped(Village, village_id, user)
    if not can_submit_for_village(user, village):
        raise ScopeError("You cannot submit entries for this village.")

    committee_id = _integer(payload.get("committee_id"), "committee_id", minimum=1)
    committee = require_scoped(Committee, committee_id, user)
    if committee.village_id != village.id:
        raise EntryValidationError("The committee does not belong to the selected village.")
    return village, committee


def _coordinates(payload: dict[str, Any], village: Village) -> tuple[float | None, float | None, str]:
    latitude = _float_or_none(payload.get("latitude"))
    longitude = _float_or_none(payload.get("longitude"))
    if latitude is None or longitude is None:
        return village.latitude, village.longitude, "village-fallback"
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise EntryValidationError("Coordinates are outside valid latitude/longitude ranges.")
    return latitude, longitude, "device"


def _resolve_executable_plan(
    payload: dict[str, Any],
    user: User,
    committee: Committee,
    expected_type: ActionPlanType,
) -> ActionPlan:
    plan_id = _integer(payload.get("action_plan_id"), "action_plan_id", minimum=1)
    action_plan = require_scoped(ActionPlan, plan_id, user)
    if action_plan.committee_id != committee.id:
        raise EntryValidationError("The action plan does not belong to the selected committee.")
    if not action_plan.is_executable:
        raise EntryValidationError("This action plan is not assigned yet. Ask your PC to complete the monthly plan.")
    if action_plan.plan_month != current_month():
        raise EntryValidationError("This action plan belongs to immutable monthly history and can no longer receive a field submission.")
    if action_plan.plan_type != expected_type:
        raise EntryValidationError(f"The selected action plan is not a {expected_type.value} plan.")
    return action_plan


def _selected_members(committee: Committee, raw_ids: Any) -> list[CommitteeMember]:
    ids = _member_ids(raw_ids)
    if not ids:
        return []
    rows = list(
        db.session.scalars(
            db.select(CommitteeMember)
            .where(
                CommitteeMember.id.in_(ids),
                CommitteeMember.committee_id == committee.id,
                CommitteeMember.is_enabled.is_(True),
                CommitteeMember.is_deleted.is_(False),
            )
            .order_by(CommitteeMember.designation, CommitteeMember.full_name)
        )
    )
    if len(rows) != len(ids):
        raise EntryValidationError(
            "One or more selected committee members do not belong to this committee or are unavailable."
        )
    for member in rows:
        if member.designation not in VISIT_DESIGNATIONS:
            raise EntryValidationError(
                f"{member.full_name} has an unsupported designation in master data."
            )
    return rows


def create_attendance(
    payload: dict[str, Any],
    photo: FileStorage | None,
    user: User,
) -> tuple[AttendanceEntry, bool]:
    client_id = _submission_id(payload.get("client_submission_id"))
    existing = db.session.scalar(
        db.select(AttendanceEntry).where(AttendanceEntry.client_submission_id == client_id)
    )
    if existing:
        if existing.submitted_by_user_id != user.id and user.role != Role.ADMIN:
            raise ScopeError("That submission identifier belongs to another user.")
        return existing, False

    village, committee = _resolve_chain(payload, user)
    action_plan = _resolve_executable_plan(payload, user, committee, ActionPlanType.ATTENDANCE)

    visit_date = _date(payload.get("visit_date"), "visit_date")
    status = attendance_status(action_plan.assigned_date, visit_date)
    reason = str(payload.get("reason") or "").strip() or None
    if status in {AttendanceStatus.EARLY, AttendanceStatus.POSTPONED} and not reason:
        raise EntryValidationError(f"A reason is required for {status.value} attendance.")

    male = _integer(payload.get("male_count", 0), "male_count")
    female = _integer(payload.get("female_count", 0), "female_count")
    new_members = _integer(payload.get("new_members_count", 0), "new_members_count")
    selected_members = _selected_members(committee, payload.get("visit_member_ids"))
    designations = list(dict.fromkeys(member.designation for member in selected_members if member.designation))
    latitude, longitude, geolocation_source = _coordinates(payload, village)

    photo_path = save_photo(photo, "attendance", client_id)
    entry = AttendanceEntry(
        village_id=village.id,
        committee_id=committee.id,
        action_plan_id=action_plan.id,
        visit_date=visit_date,
        male_count=male,
        female_count=female,
        total_count=male + female,
        new_members_count=new_members,
        visit_designations=designations,
        status=status,
        reason=reason,
        remarks=str(payload.get("remarks") or "").strip() or None,
        photo_path=photo_path,
        latitude=latitude,
        longitude=longitude,
        geolocation_source=geolocation_source,
        submitted_by_user_id=user.id,
        client_submission_id=client_id,
    )
    db.session.add(entry)
    try:
        db.session.flush()
        for member in selected_members:
            db.session.add(
                AttendanceVisitMember(
                    attendance_entry_id=entry.id,
                    committee_member_id=member.id,
                    member_name_snapshot=member.full_name,
                    designation_snapshot=member.designation or "Member",
                    gender_snapshot=member.gender,
                )
            )
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        delete_photo(photo_path)
        duplicate = db.session.scalar(
            db.select(AttendanceEntry).where(AttendanceEntry.client_submission_id == client_id)
        )
        if duplicate:
            return duplicate, False
        if db.session.scalar(
            db.select(AttendanceEntry).where(AttendanceEntry.action_plan_id == action_plan.id)
        ):
            raise EntryValidationError("Attendance has already been submitted for this action plan.") from exc
        raise

    record_audit(AuditAction.CREATE, entry, after=model_snapshot(entry), actor=user)
    return entry, True


def create_specials(
    payload: dict[str, Any],
    photo: FileStorage | None,
    user: User,
) -> tuple[SpecialsEntry, bool]:
    client_id = _submission_id(payload.get("client_submission_id"))
    existing = db.session.scalar(
        db.select(SpecialsEntry).where(SpecialsEntry.client_submission_id == client_id)
    )
    if existing:
        if existing.submitted_by_user_id != user.id and user.role != Role.ADMIN:
            raise ScopeError("That submission identifier belongs to another user.")
        return existing, False

    village, committee = _resolve_chain(payload, user)
    action_plan = _resolve_executable_plan(payload, user, committee, ActionPlanType.SPECIALS)

    scope_value = str(payload.get("scope") or "").strip()
    try:
        scope = next(item for item in SpecialScope if item.value == scope_value or item.name == scope_value)
    except StopIteration as exc:
        raise EntryValidationError("Scope must be Under GP or Under VDC.") from exc

    event_date = _date(payload.get("event_date"), "event_date")
    status = attendance_status(action_plan.assigned_date, event_date)
    reason = str(payload.get("reason") or "").strip() or None
    if status in {AttendanceStatus.EARLY, AttendanceStatus.POSTPONED} and not reason:
        raise EntryValidationError(f"A reason is required for {status.value} Specials entry.")

    participant_count = _integer(payload.get("participant_count"), "participant_count")
    latitude, longitude, geolocation_source = _coordinates(payload, village)
    photo_path = save_photo(photo, "specials", client_id)

    entry = SpecialsEntry(
        village_id=village.id,
        committee_id=committee.id,
        action_plan_id=action_plan.id,
        event_date=event_date,
        title=str(payload.get("title") or "").strip() or committee.name,
        participant_count=participant_count,
        scope=scope,
        status=status,
        reason=reason,
        notes=str(payload.get("notes") or "").strip() or None,
        photo_path=photo_path,
        latitude=latitude,
        longitude=longitude,
        geolocation_source=geolocation_source,
        submitted_by_user_id=user.id,
        client_submission_id=client_id,
    )
    db.session.add(entry)
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        delete_photo(photo_path)
        duplicate = db.session.scalar(
            db.select(SpecialsEntry).where(SpecialsEntry.client_submission_id == client_id)
        )
        if duplicate:
            return duplicate, False
        if db.session.scalar(
            db.select(SpecialsEntry).where(SpecialsEntry.action_plan_id == action_plan.id)
        ):
            raise EntryValidationError("A Specials entry has already been submitted for this action plan.") from exc
        raise

    record_audit(AuditAction.CREATE, entry, after=model_snapshot(entry), actor=user)
    return entry, True
