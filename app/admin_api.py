from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from .extensions import db
from .models import (
    DA,
    PC,
    PM,
    ActionPlan,
    ActionPlanType,
    AttendanceEntry,
    AttendanceStatus,
    AuditAction,
    AuditLog,
    Cluster,
    Committee,
    CommitteeMember,
    RecycleBin,
    Role,
    SpecialScope,
    SpecialsEntry,
    User,
    Village,
)
from .services.audit import (
    display_name,
    model_snapshot,
    record_audit,
    soft_delete,
)
from .services.audit import (
    restore as restore_record,
)
from .services.entries import (
    EntryValidationError,
    attendance_status,
    create_attendance,
    create_specials,
)

bp = Blueprint("admin_api", __name__, url_prefix="/api/v1/admin")


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str = "text"
    required: bool = False
    label: str | None = None
    choices: tuple[str, ...] = ()
    related_resource: str | None = None
    readonly: bool = False
    hidden: bool = False
    min: int | float | None = None


@dataclass(frozen=True)
class ResourceSpec:
    model: type
    label: str
    fields: tuple[FieldSpec, ...]
    search: tuple[str, ...]
    columns: tuple[str, ...]
    parent_fields: tuple[str, ...] = ()
    allow_create: bool = True


COMMON_LIFECYCLE = (
    FieldSpec("is_enabled", "boolean", label="Enabled"),
)

RESOURCES: dict[str, ResourceSpec] = {
    "pms": ResourceSpec(
        PM,
        "Program Managers",
        (
            FieldSpec("full_name", required=True),
            FieldSpec("email", "email"),
            FieldSpec("mobile", "tel"),
            FieldSpec("notes", "textarea"),
            *COMMON_LIFECYCLE,
        ),
        ("full_name", "email", "mobile"),
        ("id", "full_name", "email", "mobile", "is_enabled"),
    ),
    "pcs": ResourceSpec(
        PC,
        "Project Coordinators",
        (
            FieldSpec("full_name", required=True),
            FieldSpec("cluster", "select", required=True, choices=("CSRB", "PDTC")),
            FieldSpec("email", "email"),
            FieldSpec("mobile", "tel"),
            FieldSpec("notes", "textarea"),
            *COMMON_LIFECYCLE,
        ),
        ("full_name", "email", "mobile"),
        ("id", "full_name", "cluster", "email", "mobile", "is_enabled"),
        ("cluster",),
    ),
    "das": ResourceSpec(
        DA,
        "Development Agents",
        (
            FieldSpec("full_name", required=True),
            FieldSpec("pc_id", "relationship", required=True, related_resource="pcs"),
            FieldSpec("email", "email"),
            FieldSpec("mobile", "tel"),
            FieldSpec("notes", "textarea"),
            *COMMON_LIFECYCLE,
        ),
        ("full_name", "email", "mobile"),
        ("id", "full_name", "pc_name", "cluster", "mobile", "is_enabled"),
        ("pc_id",),
    ),
    "villages": ResourceSpec(
        Village,
        "Villages",
        (
            FieldSpec("name", required=True),
            FieldSpec("code"),
            FieldSpec("gp_name", label="Gram Panchayat"),
            FieldSpec("district"),
            FieldSpec("mandal"),
            FieldSpec("latitude", "number"),
            FieldSpec("longitude", "number"),
            FieldSpec("da_id", "relationship", required=True, related_resource="das"),
            FieldSpec("notes", "textarea"),
            *COMMON_LIFECYCLE,
        ),
        ("name", "code", "gp_name", "district", "mandal"),
        ("id", "name", "gp_name", "da_name", "cluster", "latitude", "longitude", "is_enabled"),
        ("da_id",),
    ),
    "committees": ResourceSpec(
        Committee,
        "Committees",
        (
            FieldSpec("name", required=True),
            FieldSpec("committee_type"),
            FieldSpec("village_id", "relationship", required=True, related_resource="villages"),
            FieldSpec("notes", "textarea"),
            *COMMON_LIFECYCLE,
        ),
        ("name", "committee_type"),
        ("id", "name", "committee_type", "village_name", "cluster", "member_total", "is_enabled"),
        ("village_id",),
    ),
    "committee-members": ResourceSpec(
        CommitteeMember,
        "Committee Members",
        (
            FieldSpec("committee_id", "relationship", required=True, related_resource="committees"),
            FieldSpec("full_name", required=True),
            FieldSpec("gender", "select", choices=("Female", "Male", "Other", "Not stated")),
            FieldSpec("designation", "select", choices=("President", "Vice President", "Secretary", "Member")),
            FieldSpec("mobile", "tel"),
            FieldSpec("notes", "textarea"),
            *COMMON_LIFECYCLE,
        ),
        ("full_name", "mobile", "designation"),
        ("id", "full_name", "designation", "gender", "committee_name", "village_name", "is_enabled"),
        ("committee_id",),
    ),
    "action-plans": ResourceSpec(
        ActionPlan,
        "Action Plans",
        (
            FieldSpec("committee_id", "relationship", required=True, related_resource="committees"),
            FieldSpec("title", required=True),
            FieldSpec("description", "textarea"),
            FieldSpec("plan_month", "date", label="Plan month"),
            FieldSpec("plan_type", "select", choices=("Attendance", "Specials")),
            FieldSpec("assigned_date", "date"),
            FieldSpec("notes", "textarea"),
            *COMMON_LIFECYCLE,
        ),
        ("title", "description"),
        ("id", "title", "plan_month", "plan_type", "assigned_date", "committee_name", "village_name", "entry_status", "is_enabled"),
        ("committee_id",),
    ),
    "attendance-entries": ResourceSpec(
        AttendanceEntry,
        "Attendance Entries",
        (
            FieldSpec("village_id", "relationship", required=True, related_resource="villages"),
            FieldSpec("committee_id", "relationship", required=True, related_resource="committees"),
            FieldSpec("action_plan_id", "relationship", required=True, related_resource="action-plans"),
            FieldSpec("visit_date", "date", required=True),
            FieldSpec("male_count", "integer", required=True, min=0),
            FieldSpec("female_count", "integer", required=True, min=0),
            FieldSpec("new_members_count", "integer", min=0),
            FieldSpec("visit_designations", "json"),
            FieldSpec("reason", "textarea"),
            FieldSpec("remarks", "textarea"),
            FieldSpec("latitude", "number"),
            FieldSpec("longitude", "number"),
            FieldSpec("client_submission_id"),
            *COMMON_LIFECYCLE,
        ),
        ("client_submission_id", "reason", "remarks"),
        ("id", "village_name", "action_plan_title", "visit_date", "total_count", "status", "submitted_by", "is_enabled"),
        ("village_id", "committee_id", "action_plan_id"),
    ),
    "specials-entries": ResourceSpec(
        SpecialsEntry,
        "Specials Entries",
        (
            FieldSpec("village_id", "relationship", required=True, related_resource="villages"),
            FieldSpec("committee_id", "relationship", required=True, related_resource="committees"),
            FieldSpec("action_plan_id", "relationship", related_resource="action-plans"),
            FieldSpec("event_date", "date", required=True),
            FieldSpec("title"),
            FieldSpec("participant_count", "integer", required=True, min=0),
            FieldSpec("scope", "select", required=True, choices=("Under GP", "Under VDC")),
            FieldSpec("reason", "textarea"),
            FieldSpec("notes", "textarea"),
            FieldSpec("latitude", "number"),
            FieldSpec("longitude", "number"),
            FieldSpec("client_submission_id"),
            *COMMON_LIFECYCLE,
        ),
        ("client_submission_id", "title", "notes"),
        ("id", "village_name", "committee_name", "event_date", "participant_count", "scope", "status", "submitted_by", "is_enabled"),
        ("village_id", "committee_id", "action_plan_id"),
    ),
    "users": ResourceSpec(
        User,
        "Users",
        (
            FieldSpec("display_name", required=True),
            FieldSpec("email", "email"),
            FieldSpec("mobile", "tel"),
            FieldSpec("password", "password", label="Password"),
            FieldSpec("role", "select", required=True, choices=("admin", "pm", "pc", "da")),
            FieldSpec("pm_id", "relationship", related_resource="pms"),
            FieldSpec("pc_id", "relationship", related_resource="pcs"),
            FieldSpec("da_id", "relationship", related_resource="das"),
            *COMMON_LIFECYCLE,
        ),
        ("display_name", "email", "mobile"),
        ("id", "display_name", "role", "email", "mobile", "profile_name", "last_login_at", "is_enabled"),
        ("role", "pm_id", "pc_id", "da_id"),
    ),
}


MODEL_BY_NAME = {spec.model.__name__: spec.model for spec in RESOURCES.values()}


@bp.before_request
def admin_guard():
    if not current_user.is_authenticated:
        return jsonify(error="Authentication required."), 401
    if current_user.role != Role.ADMIN:
        return jsonify(error="Administrator access required."), 403
    return None


def _field_json(item: FieldSpec) -> dict[str, Any]:
    result = {
        "name": item.name,
        "type": item.type,
        "required": item.required,
        "label": item.label,
        "readonly": item.readonly,
        "hidden": item.hidden,
    }
    if item.choices:
        result["choices"] = list(item.choices)
    if item.related_resource:
        result["related_resource"] = item.related_resource
    if item.min is not None:
        result["min"] = item.min
    return result


@bp.get("/resources")
def resources():
    return jsonify(
        resources={
            slug: {
                "slug": slug,
                "label": spec.label,
                "fields": [_field_json(item) for item in spec.fields],
                "columns": list(spec.columns),
                "allow_create": spec.allow_create,
            }
            for slug, spec in RESOURCES.items()
        }
    )


def _serialize(record: Any) -> dict[str, Any]:
    data = model_snapshot(record)
    if isinstance(record, DA):
        data.update(pc_name=record.pc.full_name, cluster=record.pc.cluster.value)
    elif isinstance(record, Village):
        data.update(
            da_name=record.da.full_name,
            pc_name=record.da.pc.full_name,
            cluster=record.da.pc.cluster.value,
        )
    elif isinstance(record, Committee):
        count = db.session.scalar(
            db.select(func.count(CommitteeMember.id)).where(
                CommitteeMember.committee_id == record.id,
                CommitteeMember.is_deleted.is_(False),
                CommitteeMember.is_enabled.is_(True),
            )
        )
        data.update(
            village_name=record.village.name,
            da_name=record.village.da.full_name,
            cluster=record.village.da.pc.cluster.value,
            member_total=count or 0,
        )
    elif isinstance(record, CommitteeMember):
        data.update(
            committee_name=record.committee.name,
            village_name=record.committee.village.name,
            cluster=record.committee.village.da.pc.cluster.value,
        )
    elif isinstance(record, ActionPlan):
        from .services.monthly_plans import action_plan_status
        data.update(
            plan_type=record.plan_type.value if record.plan_type else None,
            committee_name=record.committee.name,
            village_name=record.committee.village.name,
            cluster=record.committee.village.da.pc.cluster.value,
            entry_status=action_plan_status(record),
        )
    elif isinstance(record, AttendanceEntry):
        data.update(
            village_name=record.village.name,
            committee_name=record.committee.name,
            action_plan_title=record.action_plan.title,
            status=record.status.value,
            submitted_by=record.submitted_by.display_name,
            cluster=record.village.da.pc.cluster.value,
        )
    elif isinstance(record, SpecialsEntry):
        data.update(
            village_name=record.village.name,
            committee_name=record.committee.name,
            scope=record.scope.value,
            status=record.status.value if record.status else None,
            submitted_by=record.submitted_by.display_name,
            cluster=record.village.da.pc.cluster.value,
        )
    elif isinstance(record, User):
        profile = record.pm or record.pc or record.da
        data.update(role=record.role.value, profile_name=display_name(profile) if profile else None)
    return data


def _resource(slug: str) -> ResourceSpec:
    spec = RESOURCES.get(slug)
    if not spec:
        raise LookupError("Unknown administrative resource.")
    return spec


def _relationship_options(stmt, model: type):
    if model is DA:
        return stmt.options(selectinload(DA.pc))
    if model is Village:
        return stmt.options(selectinload(Village.da).selectinload(DA.pc))
    if model is Committee:
        return stmt.options(selectinload(Committee.village).selectinload(Village.da).selectinload(DA.pc))
    if model is CommitteeMember:
        return stmt.options(
            selectinload(CommitteeMember.committee)
            .selectinload(Committee.village)
            .selectinload(Village.da)
            .selectinload(DA.pc)
        )
    if model is ActionPlan:
        return stmt.options(
            selectinload(ActionPlan.committee)
            .selectinload(Committee.village)
            .selectinload(Village.da)
            .selectinload(DA.pc),
            selectinload(ActionPlan.attendance_entry),
            selectinload(ActionPlan.specials_entry),
        )
    if model is AttendanceEntry:
        return stmt.options(
            selectinload(AttendanceEntry.village).selectinload(Village.da).selectinload(DA.pc),
            selectinload(AttendanceEntry.committee),
            selectinload(AttendanceEntry.action_plan),
            selectinload(AttendanceEntry.submitted_by),
        )
    if model is SpecialsEntry:
        return stmt.options(
            selectinload(SpecialsEntry.village).selectinload(Village.da).selectinload(DA.pc),
            selectinload(SpecialsEntry.committee),
            selectinload(SpecialsEntry.action_plan),
            selectinload(SpecialsEntry.submitted_by),
        )
    return stmt


@bp.route("/<slug>", methods=["GET", "POST"])
def collection(slug: str):
    try:
        spec = _resource(slug)
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    if request.method == "GET":
        stmt = db.select(spec.model).where(spec.model.is_deleted.is_(False))
        include_disabled = request.args.get("include_disabled", "1") == "1"
        if not include_disabled:
            stmt = stmt.where(spec.model.is_enabled.is_(True))
        query = request.args.get("q", "").strip()
        if query and spec.search:
            stmt = stmt.where(or_(*[getattr(spec.model, name).ilike(f"%{query}%") for name in spec.search]))
        stmt = _relationship_options(stmt, spec.model).order_by(spec.model.id.desc())
        try:
            page = max(1, int(request.args.get("page", "1")))
            per_page = min(500, max(1, int(request.args.get("per_page", "25"))))
        except ValueError:
            page, per_page = 1, 25
        pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
        return jsonify(
            items=[_serialize(item) for item in pagination.items],
            page=pagination.page,
            pages=pagination.pages,
            total=pagination.total,
        )

    data = dict(request.get_json(silent=True) or {})
    try:
        record = _create(spec, data)
        db.session.commit()
        return jsonify(item=_serialize(record)), 201
    except EntryValidationError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422
    except IntegrityError as exc:
        db.session.rollback()
        return jsonify(error=_integrity_message(exc)), 409
    except (TypeError, ValueError) as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422


@bp.patch("/<slug>/<int:record_id>")
def update(slug: str, record_id: int):
    try:
        spec = _resource(slug)
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    record = db.session.get(spec.model, record_id)
    if record is None or record.is_deleted:
        return jsonify(error="Record not found."), 404
    data = dict(request.get_json(silent=True) or {})
    acknowledge = bool(data.pop("acknowledge_move", False))
    before = model_snapshot(record)
    try:
        changed_parent = _apply(record, spec, data, is_create=False)
        if changed_parent:
            _validate_move(record, spec, acknowledge)
        _validate_record(record)
        after = model_snapshot(record)
        changed = before != after
        if changed:
            record_audit(AuditAction.MOVE if changed_parent else AuditAction.UPDATE, record, before=before, after=after)
        db.session.commit()
        return jsonify(item=_serialize(record))
    except EntryValidationError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422
    except IntegrityError as exc:
        db.session.rollback()
        return jsonify(error=_integrity_message(exc)), 409
    except (TypeError, ValueError) as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 409 if "move" in str(exc).lower() else 422


@bp.post("/<slug>/<int:record_id>/toggle")
def toggle(slug: str, record_id: int):
    try:
        spec = _resource(slug)
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    record = db.session.get(spec.model, record_id)
    if record is None or record.is_deleted:
        return jsonify(error="Record not found."), 404
    if isinstance(record, User) and record.id == current_user.id and record.is_enabled:
        return jsonify(error="You cannot disable your own account."), 409
    requested = (request.get_json(silent=True) or {}).get("is_enabled")
    next_value = not record.is_enabled if requested is None else bool(requested)
    if record.is_enabled == next_value:
        return jsonify(item=_serialize(record))
    before = model_snapshot(record)
    record.is_enabled = next_value
    record_audit(
        AuditAction.ENABLE if next_value else AuditAction.DISABLE,
        record,
        before=before,
        after=model_snapshot(record),
    )
    db.session.commit()
    return jsonify(item=_serialize(record))


@bp.delete("/<slug>/<int:record_id>")
def delete(slug: str, record_id: int):
    try:
        spec = _resource(slug)
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    record = db.session.get(spec.model, record_id)
    if record is None or record.is_deleted:
        return jsonify(error="Record not found."), 404
    if isinstance(record, User) and record.id == current_user.id:
        return jsonify(error="You cannot delete your own account."), 409
    dependency = _active_dependency(record)
    if dependency:
        return jsonify(error=dependency), 409
    row = soft_delete(record, current_user._get_current_object(), current_app.config["RECYCLE_RETENTION_DAYS"])
    db.session.commit()
    return jsonify(recycle_bin_id=row.id, purge_after=row.purge_after.isoformat())


@bp.get("/recycle-bin/items")
def recycle_items():
    rows = db.session.scalars(
        db.select(RecycleBin)
        .where(RecycleBin.restored_at.is_(None))
        .order_by(RecycleBin.deleted_at.desc())
    ).all()
    return jsonify(
        items=[
            {
                "id": row.id,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "display_name": row.display_name,
                "deleted_at": row.deleted_at.isoformat(),
                "purge_after": row.purge_after.isoformat(),
                "snapshot_json": row.snapshot_json,
            }
            for row in rows
        ],
        total=len(rows),
    )


@bp.post("/recycle-bin/<int:item_id>/restore")
def restore(item_id: int):
    row = db.session.get(RecycleBin, item_id)
    if row is None or row.restored_at is not None:
        return jsonify(error="Recycle-bin item not found."), 404
    model = MODEL_BY_NAME.get(row.entity_type)
    if not model:
        return jsonify(error="The record type is no longer restorable."), 409
    record = db.session.get(model, row.entity_id)
    if record is None:
        return jsonify(error="The underlying record has already been purged."), 410
    dependency = _missing_parent(record)
    if dependency:
        return jsonify(error=dependency), 409
    try:
        restore_record(record, row, current_user._get_current_object())
        db.session.commit()
        return jsonify(item=_serialize(record))
    except (ValueError, IntegrityError) as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 409


@bp.get("/audit-logs/items")
def audit_logs():
    try:
        per_page = min(500, max(1, int(request.args.get("per_page", "100"))))
    except ValueError:
        per_page = 100
    rows = db.session.scalars(
        db.select(AuditLog)
        .options(selectinload(AuditLog.actor))
        .order_by(AuditLog.created_at.desc())
        .limit(per_page)
    ).all()
    return jsonify(
        items=[
            {
                "id": row.id,
                "created_at": row.created_at.isoformat(),
                "actor_user_id": row.actor_user_id,
                "actor_name": row.actor.display_name if row.actor else "System",
                "action": row.action.value,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "before_json": row.before_json,
                "after_json": row.after_json,
                "request_id": row.request_id,
            }
            for row in rows
        ],
        total=len(rows),
    )


def _create(spec: ResourceSpec, data: dict[str, Any]):
    if not spec.allow_create:
        raise EntryValidationError("Creation is not available for this resource.")
    if spec.model is AttendanceEntry:
        record, _ = create_attendance(data, None, current_user._get_current_object())
        return record
    if spec.model is SpecialsEntry:
        record, _ = create_specials(data, None, current_user._get_current_object())
        return record

    record = spec.model()
    _apply(record, spec, data, is_create=True)
    if isinstance(record, User):
        password = str(data.get("password") or "")
        if len(password) < 10:
            raise EntryValidationError("New user passwords must contain at least 10 characters.")
        record.set_password(password)
    if isinstance(record, ActionPlan):
        record.assigned_by_user_id = current_user.id
    _validate_record(record)
    db.session.add(record)
    db.session.flush()
    record_audit(AuditAction.CREATE, record, after=model_snapshot(record))
    return record


def _convert(field_spec: FieldSpec, value: Any) -> Any:
    if value is None or value == "":
        return None
    if field_spec.type in {"integer", "relationship"}:
        return int(value)
    if field_spec.type == "number":
        return float(value)
    if field_spec.type == "boolean":
        return bool(value)
    if field_spec.type == "date":
        return date.fromisoformat(str(value))
    if field_spec.type == "datetime":
        return datetime.fromisoformat(str(value))
    if field_spec.type == "json":
        if not isinstance(value, (list, dict)):
            raise EntryValidationError(f"{field_spec.label or field_spec.name} must be JSON.")
        return value
    return str(value).strip() or None


def _apply(record: Any, spec: ResourceSpec, data: dict[str, Any], *, is_create: bool) -> bool:
    changed_parent = False
    allowed = {item.name: item for item in spec.fields}
    for name, value in data.items():
        if name in {"password", "acknowledge_move"}:
            continue
        field_spec = allowed.get(name)
        if field_spec is None or field_spec.readonly:
            continue
        converted = _convert(field_spec, value)
        if field_spec.required and converted is None:
            raise EntryValidationError(f"{field_spec.label or name} is required.")
        if field_spec.min is not None and converted is not None and converted < field_spec.min:
            raise EntryValidationError(f"{field_spec.label or name} must be at least {field_spec.min}.")
        if name == "role" and converted is not None:
            converted = Role(converted)
        elif name == "cluster" and converted is not None:
            converted = Cluster(converted)
        elif name == "plan_type" and converted is not None:
            converted = ActionPlanType(converted)
        elif name == "scope" and converted is not None:
            converted = next(
                (item for item in SpecialScope if item.value == converted or item.name == converted),
                None,
            )
            if converted is None:
                raise EntryValidationError("Scope must be Under GP or Under VDC.")
        old = getattr(record, name, None)
        if not is_create and name in spec.parent_fields and old != converted:
            changed_parent = True
        setattr(record, name, converted)

    if isinstance(record, User):
        record.email = record.email.casefold() if record.email else None
        record.mobile = "".join(ch for ch in record.mobile if ch.isdigit() or ch == "+") if record.mobile else None
        password = data.get("password")
        if password:
            if len(str(password)) < 10:
                raise EntryValidationError("Passwords must contain at least 10 characters.")
            record.set_password(str(password))
    return changed_parent


def _validate_record(record: Any) -> None:
    if isinstance(record, User):
        if record.role == Role.ADMIN:
            if any((record.pm_id, record.pc_id, record.da_id)):
                raise EntryValidationError("Admin users cannot be attached to PM, PC or DA profiles.")
        elif record.role == Role.PM:
            if not record.pm_id or record.pc_id or record.da_id:
                raise EntryValidationError("PM users require only a PM profile.")
        elif record.role == Role.PC:
            if not record.pc_id or record.pm_id or record.da_id:
                raise EntryValidationError("PC users require only a PC profile.")
        elif record.role == Role.DA:
            if not record.da_id or record.pm_id or record.pc_id:
                raise EntryValidationError("DA users require only a DA profile.")
        if not record.email and not record.mobile:
            raise EntryValidationError("A user requires an email address or mobile number.")

    if isinstance(record, ActionPlan):
        if record.plan_month:
            record.plan_month = record.plan_month.replace(day=1)
        if record.assigned_date and not record.plan_type:
            raise EntryValidationError("Choose Attendance or Specials before assigning a date.")
        if (record.plan_type or record.assigned_date) and not record.plan_month:
            raise EntryValidationError("Assigned Action Plans must have a Plan Month.")
        if record.assigned_date and record.plan_month and (
            record.assigned_date.year != record.plan_month.year
            or record.assigned_date.month != record.plan_month.month
        ):
            raise EntryValidationError("Assigned Date must be inside the Action Plan month.")

    if isinstance(record, AttendanceEntry):
        village = db.session.get(Village, record.village_id)
        committee = db.session.get(Committee, record.committee_id)
        plan = db.session.get(ActionPlan, record.action_plan_id)
        if not all((village, committee, plan)):
            raise EntryValidationError("Attendance village, committee and action plan must exist.")
        if committee.village_id != village.id or plan.committee_id != committee.id:
            raise EntryValidationError("Attendance hierarchy is inconsistent.")
        if plan.assigned_date is None:
            raise EntryValidationError("Action plan must have an assigned date.")
        record.total_count = int(record.male_count or 0) + int(record.female_count or 0)
        record.status = attendance_status(plan.assigned_date, record.visit_date)
        if record.status in {AttendanceStatus.EARLY, AttendanceStatus.POSTPONED} and not record.reason:
            raise EntryValidationError(f"A reason is required for {record.status.value} attendance.")

    if isinstance(record, SpecialsEntry):
        village = db.session.get(Village, record.village_id)
        committee = db.session.get(Committee, record.committee_id)
        plan = db.session.get(ActionPlan, record.action_plan_id) if record.action_plan_id else None
        if not village or not committee or committee.village_id != village.id:
            raise EntryValidationError("Specials hierarchy is inconsistent.")
        if plan:
            if plan.committee_id != committee.id or not plan.is_executable or plan.plan_type != ActionPlanType.SPECIALS:
                raise EntryValidationError("Specials action plan is inconsistent.")
            record.status = attendance_status(plan.assigned_date, record.event_date)
            if record.status in {AttendanceStatus.EARLY, AttendanceStatus.POSTPONED} and not record.reason:
                raise EntryValidationError(f"A reason is required for {record.status.value} Specials entry.")


def _validate_move(record: Any, spec: ResourceSpec, acknowledge: bool) -> None:
    if isinstance(record, DA):
        historical = db.session.scalar(
            db.select(func.count(AttendanceEntry.id))
            .join(AttendanceEntry.village)
            .where(Village.da_id == record.id, AttendanceEntry.is_deleted.is_(False))
        ) or db.session.scalar(
            db.select(func.count(SpecialsEntry.id))
            .join(SpecialsEntry.village)
            .where(Village.da_id == record.id, SpecialsEntry.is_deleted.is_(False))
        )
        if historical and not acknowledge:
            raise ValueError("This move changes inherited cluster reporting for historical submissions; acknowledge the move to continue.")
    elif isinstance(record, Village):
        historical = db.session.scalar(
            db.select(func.count(AttendanceEntry.id)).where(
                AttendanceEntry.village_id == record.id, AttendanceEntry.is_deleted.is_(False)
            )
        ) or db.session.scalar(
            db.select(func.count(SpecialsEntry.id)).where(
                SpecialsEntry.village_id == record.id, SpecialsEntry.is_deleted.is_(False)
            )
        )
        if historical and not acknowledge:
            raise ValueError("This move changes inherited cluster reporting for historical submissions; acknowledge the move to continue.")
    elif isinstance(record, Committee):
        has_entries = db.session.scalar(
            db.select(func.count(AttendanceEntry.id)).where(
                AttendanceEntry.committee_id == record.id, AttendanceEntry.is_deleted.is_(False)
            )
        ) or db.session.scalar(
            db.select(func.count(SpecialsEntry.id)).where(
                SpecialsEntry.committee_id == record.id, SpecialsEntry.is_deleted.is_(False)
            )
        )
        if has_entries:
            raise ValueError("A committee with historical entries cannot be moved; create a new committee or migrate its entries explicitly.")
    elif isinstance(record, ActionPlan) and record.attendance_entry and not record.attendance_entry.is_deleted:
        raise ValueError("An action plan with attendance cannot be moved to another committee.")
    elif isinstance(record, (AttendanceEntry, SpecialsEntry)):
        if not acknowledge:
            raise ValueError("Moving a historical submission requires explicit acknowledgement.")


def _active_dependency(record: Any) -> str | None:
    checks: list[tuple[str, type, Any]] = []
    if isinstance(record, PM):
        checks.append(("user account", User, User.pm_id == record.id))
    elif isinstance(record, PC):
        checks.extend([
            ("development agent", DA, DA.pc_id == record.id),
            ("user account", User, User.pc_id == record.id),
        ])
    elif isinstance(record, DA):
        checks.extend([
            ("village", Village, Village.da_id == record.id),
            ("user account", User, User.da_id == record.id),
        ])
    elif isinstance(record, Village):
        checks.extend([
            ("committee", Committee, Committee.village_id == record.id),
            ("attendance entry", AttendanceEntry, AttendanceEntry.village_id == record.id),
            ("specials entry", SpecialsEntry, SpecialsEntry.village_id == record.id),
        ])
    elif isinstance(record, Committee):
        checks.extend([
            ("committee member", CommitteeMember, CommitteeMember.committee_id == record.id),
            ("action plan", ActionPlan, ActionPlan.committee_id == record.id),
            ("attendance entry", AttendanceEntry, AttendanceEntry.committee_id == record.id),
            ("specials entry", SpecialsEntry, SpecialsEntry.committee_id == record.id),
        ])
    elif isinstance(record, ActionPlan):
        checks.append(("attendance entry", AttendanceEntry, AttendanceEntry.action_plan_id == record.id))

    for label, model, condition in checks:
        count = db.session.scalar(
            db.select(func.count(model.id)).where(
                condition,
                model.is_deleted.is_(False),
            )
        )
        if count:
            return f"Move or delete the active {label} records first."
    return None


def _missing_parent(record: Any) -> str | None:
    parents: list[Any] = []
    if isinstance(record, DA):
        parents = [record.pc]
    elif isinstance(record, Village):
        parents = [record.da]
    elif isinstance(record, Committee):
        parents = [record.village]
    elif isinstance(record, CommitteeMember):
        parents = [record.committee]
    elif isinstance(record, ActionPlan):
        parents = [record.committee]
    elif isinstance(record, AttendanceEntry):
        parents = [record.village, record.committee, record.action_plan, record.submitted_by]
    elif isinstance(record, SpecialsEntry):
        parents = [record.village, record.committee, record.submitted_by]
    elif isinstance(record, User):
        parents = [parent for parent in (record.pm, record.pc, record.da) if parent is not None]
    if any(parent is None or getattr(parent, "is_deleted", False) for parent in parents):
        return "Restore the record's parent assignments first."
    return None


def _integrity_message(_error: IntegrityError) -> str:
    return "The change conflicts with an existing record or referenced relationship."
