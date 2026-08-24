from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from .extensions import db
from .models import (
    DA,
    PC,
    PM,
    ActionPlan,
    ActionPlanType,
    AttendanceEntry,
    AuditAction,
    Committee,
    CommitteeMember,
    Role,
    SpecialsEntry,
    Village,
)
from .scoping import (
    ScopeError,
    can_manage_action_plan,
    inherited_cluster,
    json_role_required,
    require_scoped,
    scoped_get,
    scoped_select,
)
from .services.audit import model_snapshot, record_audit
from .services.entries import EntryValidationError, create_attendance, create_specials
from .services.files import UploadProblem
from .services.monitoring import (
    action_plan_status,
    dashboard_series,
    dashboard_summary,
    map_markers,
)
from .timeutils import current_month

bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _iso(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _page(stmt, default_per_page: int = 50):
    try:
        page = max(1, int(request.args.get("page", "1")))
        per_page = min(250, max(1, int(request.args.get("per_page", default_per_page))))
    except ValueError:
        page, per_page = 1, default_per_page
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    return pagination


def _payload() -> dict[str, Any]:
    if request.is_json:
        return dict(request.get_json(silent=True) or {})
    data = request.form.to_dict()
    designations = request.form.getlist("visit_designations")
    if designations:
        data["visit_designations"] = designations
    return data


def _village_json(village: Village) -> dict[str, Any]:
    return {
        "id": village.id,
        "name": village.name,
        "code": village.code,
        "gp_name": village.gp_name,
        "district": village.district,
        "mandal": village.mandal,
        "latitude": village.latitude,
        "longitude": village.longitude,
        "da_id": village.da_id,
        "da_name": village.da.full_name,
        "pc_id": village.da.pc_id,
        "pc_name": village.da.pc.full_name,
        "cluster": village.da.pc.cluster.value,
        "is_enabled": village.is_enabled,
    }


def _committee_json(committee: Committee, member_count: int | None = None) -> dict[str, Any]:
    base = (
        CommitteeMember.committee_id == committee.id,
        CommitteeMember.is_enabled.is_(True),
        CommitteeMember.is_deleted.is_(False),
    )
    if member_count is None:
        member_count = db.session.scalar(
            db.select(func.count(CommitteeMember.id)).where(*base)
        ) or 0
    gender_counts = dict(
        db.session.execute(
            db.select(CommitteeMember.gender, func.count(CommitteeMember.id))
            .where(*base)
            .group_by(CommitteeMember.gender)
        ).all()
    )
    male = int(gender_counts.get("Male", 0))
    female = int(gender_counts.get("Female", 0))
    return {
        "id": committee.id,
        "name": committee.name,
        "committee_type": committee.committee_type,
        "village_id": committee.village_id,
        "member_total": member_count,
        "male_master": male,
        "female_master": female,
        "unknown_master": max(0, int(member_count) - male - female),
        "cluster": inherited_cluster(committee),
    }

def _plan_json(plan: ActionPlan) -> dict[str, Any]:
    attendance_id = plan.attendance_entry.id if plan.attendance_entry and not plan.attendance_entry.is_deleted else None
    specials_id = plan.specials_entry.id if plan.specials_entry and not plan.specials_entry.is_deleted else None
    return {
        "id": plan.id,
        "committee_id": plan.committee_id,
        "title": plan.title,
        "description": plan.description,
        "plan_month": _iso(plan.plan_month),
        "plan_type": plan.plan_type.value if plan.plan_type else None,
        "assigned_date": _iso(plan.assigned_date),
        "status": action_plan_status(plan),
        "attendance_entry_id": attendance_id,
        "specials_entry_id": specials_id,
        "is_executable": plan.is_executable,
        "is_enabled": plan.is_enabled,
    }

def _attendance_json(entry: AttendanceEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "client_submission_id": entry.client_submission_id,
        "village_id": entry.village_id,
        "village_name": entry.village.name,
        "committee_id": entry.committee_id,
        "committee_name": entry.committee.name,
        "action_plan_id": entry.action_plan_id,
        "action_plan_title": entry.action_plan.title,
        "visit_date": entry.visit_date.isoformat(),
        "assigned_date": _iso(entry.action_plan.assigned_date),
        "male_count": entry.male_count,
        "female_count": entry.female_count,
        "total_count": entry.total_count,
        "new_members_count": entry.new_members_count,
        "visit_designations": entry.visit_designations,
        "visit_members": [
            {
                "id": link.committee_member_id,
                "name": link.member_name_snapshot,
                "designation": link.designation_snapshot,
                "gender": link.gender_snapshot,
            }
            for link in entry.visited_members
            if link.is_enabled and not link.is_deleted
        ],
        "status": entry.status.value,
        "reason": entry.reason,
        "remarks": entry.remarks,
        "latitude": entry.latitude,
        "longitude": entry.longitude,
        "geolocation_source": entry.geolocation_source,
        "photo_url": f"/api/v1/photos/attendance/{entry.id}" if entry.photo_path else None,
        "submitted_at": entry.submitted_at.isoformat(),
        "submitted_by": entry.submitted_by.display_name,
        "cluster": inherited_cluster(entry),
    }

def _specials_json(entry: SpecialsEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "client_submission_id": entry.client_submission_id,
        "village_id": entry.village_id,
        "village_name": entry.village.name,
        "committee_id": entry.committee_id,
        "committee_name": entry.committee.name,
        "action_plan_id": entry.action_plan_id,
        "assigned_date": _iso(entry.action_plan.assigned_date) if entry.action_plan else None,
        "event_date": entry.event_date.isoformat(),
        "title": entry.title,
        "participant_count": entry.participant_count,
        "scope": entry.scope.value,
        "status": entry.status.value if entry.status else None,
        "reason": entry.reason,
        "notes": entry.notes,
        "latitude": entry.latitude,
        "longitude": entry.longitude,
        "geolocation_source": entry.geolocation_source,
        "photo_url": f"/api/v1/photos/specials/{entry.id}" if entry.photo_path else None,
        "submitted_at": entry.submitted_at.isoformat(),
        "submitted_by": entry.submitted_by.display_name,
        "cluster": inherited_cluster(entry),
    }

@bp.get("/auth/csrf")
def csrf_token():
    return jsonify(csrf_token=generate_csrf())


@bp.get("/me")
@login_required
def me():
    profile = None
    if current_user.role == Role.PM and current_user.pm:
        profile = {"id": current_user.pm.id, "name": current_user.pm.full_name}
    elif current_user.role == Role.PC and current_user.pc:
        profile = {
            "id": current_user.pc.id,
            "name": current_user.pc.full_name,
            "cluster": current_user.pc.cluster.value,
        }
    elif current_user.role == Role.DA and current_user.da:
        profile = {
            "id": current_user.da.id,
            "name": current_user.da.full_name,
            "pc_id": current_user.da.pc_id,
            "cluster": current_user.da.pc.cluster.value,
        }
    return jsonify(
        id=current_user.id,
        display_name=current_user.display_name,
        role=current_user.role.value,
        profile=profile,
        cache_context=f"user-{current_user.id}",
    )


@bp.get("/villages")
@login_required
def villages():
    stmt = (
        scoped_select(Village, current_user)
        .options(selectinload(Village.da).selectinload(DA.pc))
        .order_by(Village.name)
    )
    q = request.args.get("q", "").strip()
    if q:
        stmt = stmt.where(Village.name.ilike(f"%{q}%"))
    rows = db.session.scalars(stmt).unique().all()
    return jsonify(items=[_village_json(row) for row in rows], total=len(rows))


@bp.get("/villages/<int:village_id>/committees")
@login_required
def village_committees(village_id: int):
    require_scoped(Village, village_id, current_user)
    rows = db.session.scalars(
        scoped_select(Committee, current_user)
        .where(Committee.village_id == village_id)
        .order_by(Committee.name)
    ).all()
    counts = dict(
        db.session.execute(
            db.select(CommitteeMember.committee_id, func.count(CommitteeMember.id))
            .where(
                CommitteeMember.committee_id.in_([row.id for row in rows] or [-1]),
                CommitteeMember.is_enabled.is_(True),
                CommitteeMember.is_deleted.is_(False),
            )
            .group_by(CommitteeMember.committee_id)
        ).all()
    )
    return jsonify(items=[_committee_json(row, counts.get(row.id, 0)) for row in rows], total=len(rows))


@bp.get("/committees/<int:committee_id>/members")
@login_required
def committee_members(committee_id: int):
    require_scoped(Committee, committee_id, current_user)
    rows = list(
        db.session.scalars(
            scoped_select(CommitteeMember, current_user)
            .where(CommitteeMember.committee_id == committee_id)
            .order_by(CommitteeMember.designation, CommitteeMember.full_name)
        )
    )
    return jsonify(
        items=[
            {
                "id": row.id,
                "name": row.full_name,
                "designation": row.designation,
                "gender": row.gender,
            }
            for row in rows
        ],
        total=len(rows),
    )


@bp.get("/committees/<int:committee_id>/action-plans")
@login_required
def committee_action_plans(committee_id: int):
    require_scoped(Committee, committee_id, current_user)
    stmt = (
        scoped_select(ActionPlan, current_user)
        .where(ActionPlan.committee_id == committee_id)
        .options(
            selectinload(ActionPlan.attendance_entry),
            selectinload(ActionPlan.specials_entry),
        )
        .order_by(ActionPlan.assigned_date.desc().nullslast(), ActionPlan.id.desc())
    )
    requested_type = (request.args.get("type") or "").strip()
    if requested_type:
        try:
            stmt = stmt.where(ActionPlan.plan_type == ActionPlanType(requested_type))
        except ValueError:
            return jsonify(error="Type must be Attendance or Specials."), 422
    if request.args.get("executable") == "1":
        month_raw = (request.args.get("month") or "").strip()
        try:
            selected_month = (
                date.fromisoformat(f"{month_raw}-01").replace(day=1)
                if len(month_raw) == 7
                else current_month()
            )
        except ValueError:
            return jsonify(error="Month must use YYYY-MM format."), 422
        stmt = stmt.where(
            ActionPlan.plan_month == selected_month,
            ActionPlan.plan_type.is_not(None),
            ActionPlan.assigned_date.is_not(None),
        )
    rows = list(db.session.scalars(stmt).unique())
    pending_only = request.args.get("pending") == "1"
    items = [_plan_json(row) for row in rows]
    if pending_only:
        items = [
            item for item in items
            if item["attendance_entry_id"] is None and item["specials_entry_id"] is None
        ]
    return jsonify(items=items, total=len(items))


@bp.post("/action-plans")
@login_required
@json_role_required(Role.ADMIN, Role.PC)
def create_action_plan_route():
    """Compatibility endpoint; creates a real monthly plan, never a legacy draft."""
    data = _payload()
    try:
        committee_id = int(data.get("committee_id"))
        committee = require_scoped(Committee, committee_id, current_user)
        if not can_manage_action_plan(current_user, committee):
            raise ScopeError("You cannot assign plans for that committee.")
        plan_month_raw = str(data.get("plan_month") or "").strip()
        if len(plan_month_raw) == 7:
            plan_month_raw += "-01"
        plan_month = date.fromisoformat(plan_month_raw).replace(day=1)
        plan_type = ActionPlanType(str(data.get("plan_type") or "").strip())
        assigned_date = date.fromisoformat(str(data.get("assigned_date") or ""))
        if (assigned_date.year, assigned_date.month) != (plan_month.year, plan_month.month):
            raise EntryValidationError("Assigned date must be inside the selected month.")
        existing = db.session.scalar(
            db.select(ActionPlan).where(
                ActionPlan.committee_id == committee.id,
                ActionPlan.plan_month == plan_month,
                ActionPlan.is_deleted.is_(False),
            )
        )
        if existing:
            return jsonify(error="A monthly action plan already exists for that committee."), 409
        plan = ActionPlan(
            committee_id=committee.id,
            title=committee.name,
            description=str(data.get("description") or "").strip() or None,
            plan_month=plan_month,
            plan_type=plan_type,
            assigned_date=assigned_date,
            assigned_by_user_id=current_user.id,
            notes=str(data.get("notes") or "").strip() or None,
        )
        db.session.add(plan)
        db.session.flush()
        record_audit(AuditAction.CREATE, plan, after=model_snapshot(plan))
        db.session.commit()
        return jsonify(item=_plan_json(plan)), 201
    except ScopeError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 403
    except (ValueError, EntryValidationError, TypeError) as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422


@bp.get("/attendance")
@login_required
def list_attendance():
    stmt = (
        scoped_select(AttendanceEntry, current_user)
        .options(
            selectinload(AttendanceEntry.village).selectinload(Village.da).selectinload(DA.pc),
            selectinload(AttendanceEntry.committee),
            selectinload(AttendanceEntry.action_plan),
            selectinload(AttendanceEntry.submitted_by),
            selectinload(AttendanceEntry.visited_members),
        )
        .order_by(AttendanceEntry.visit_date.desc(), AttendanceEntry.id.desc())
    )
    pagination = _page(stmt)
    return jsonify(
        items=[_attendance_json(row) for row in pagination.items],
        page=pagination.page,
        pages=pagination.pages,
        total=pagination.total,
    )


@bp.post("/attendance")
@login_required
@json_role_required(Role.DA)
def submit_attendance():
    data = _payload()
    photo = request.files.get("photo")
    try:
        entry, created = create_attendance(data, photo, current_user._get_current_object())
        db.session.commit()
        return jsonify(item=_attendance_json(entry), idempotent=not created), 201 if created else 200
    except ScopeError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 403
    except (EntryValidationError, UploadProblem, ValueError) as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422


@bp.get("/specials")
@login_required
def list_specials():
    stmt = (
        scoped_select(SpecialsEntry, current_user)
        .options(
            selectinload(SpecialsEntry.village).selectinload(Village.da).selectinload(DA.pc),
            selectinload(SpecialsEntry.committee),
            selectinload(SpecialsEntry.action_plan),
            selectinload(SpecialsEntry.submitted_by),
        )
        .order_by(SpecialsEntry.event_date.desc(), SpecialsEntry.id.desc())
    )
    pagination = _page(stmt)
    return jsonify(
        items=[_specials_json(row) for row in pagination.items],
        page=pagination.page,
        pages=pagination.pages,
        total=pagination.total,
    )


@bp.post("/specials")
@login_required
@json_role_required(Role.DA)
def submit_specials():
    data = _payload()
    photo = request.files.get("photo")
    try:
        entry, created = create_specials(data, photo, current_user._get_current_object())
        db.session.commit()
        return jsonify(item=_specials_json(entry), idempotent=not created), 201 if created else 200
    except ScopeError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 403
    except (EntryValidationError, UploadProblem, ValueError) as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422


@bp.get("/directory")
@login_required
def directory_data():
    village_rows = db.session.scalars(
        scoped_select(Village, current_user)
        .options(selectinload(Village.da).selectinload(DA.pc))
        .order_by(Village.name)
    ).unique().all()
    da_rows = db.session.scalars(
        scoped_select(DA, current_user).options(selectinload(DA.pc)).order_by(DA.full_name)
    ).unique().all()
    pc_rows = db.session.scalars(
        scoped_select(PC, current_user)
        .options(selectinload(PC.das).selectinload(DA.villages))
        .order_by(PC.full_name)
    ).unique().all()
    pm_rows = db.session.scalars(
        scoped_select(PM, current_user).order_by(PM.full_name)
    ).unique().all()
    return jsonify(
        villages=[{**_village_json(row), "profile_url": f"/directory/village/{row.id}"} for row in village_rows],
        das=[
            {
                "id": row.id,
                "name": row.full_name,
                "pc_id": row.pc_id,
                "pc_name": row.pc.full_name,
                "cluster": row.pc.cluster.value,
                "village_count": sum(
                    1 for village in village_rows if village.da_id == row.id
                ),
            }
            for row in da_rows
        ],
        pcs=[
            {
                "id": row.id,
                "name": row.full_name,
                "cluster": row.cluster.value,
                "da_count": sum(1 for da in row.das if da.is_enabled and not da.is_deleted),
                "village_count": sum(
                    1
                    for da in row.das if da.is_enabled and not da.is_deleted
                    for village in da.villages if village.is_enabled and not village.is_deleted
                ),
                "profile_url": f"/directory/pc/{row.id}",
            }
            for row in pc_rows
        ],
        pms=[
            {
                "id": row.id,
                "name": row.full_name,
                "email": row.email,
                "mobile": row.mobile,
                "profile_url": f"/directory/pm/{row.id}",
            }
            for row in pm_rows
        ],
    )


@bp.get("/monitoring/summary")
@login_required
def monitoring_summary():
    return jsonify(dashboard_summary(current_user._get_current_object()))


@bp.get("/monitoring/series")
@login_required
@json_role_required(Role.ADMIN, Role.PM, Role.PC)
def monitoring_series_route():
    return jsonify(dashboard_series(current_user._get_current_object()))


@bp.get("/monitoring/map")
@login_required
def monitoring_map():
    return jsonify(items=map_markers(current_user._get_current_object()))


@bp.get("/photos/<entry_type>/<int:entry_id>")
@login_required
def photo(entry_type: str, entry_id: int):
    model = AttendanceEntry if entry_type == "attendance" else SpecialsEntry if entry_type == "specials" else None
    if model is None:
        return jsonify(error="Unknown photo type."), 404
    entry = scoped_get(model, entry_id, current_user, include_disabled=True)
    if entry is None or not entry.photo_path:
        return jsonify(error="Photo not found."), 404
    upload_root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    path = (upload_root / entry.photo_path).resolve()
    if upload_root not in path.parents or not path.exists():
        return jsonify(error="Photo not found."), 404
    return send_file(path, mimetype="image/webp", conditional=True, max_age=86400)


@bp.errorhandler(ScopeError)
def scope_error(error):
    return jsonify(error=str(error)), 403
