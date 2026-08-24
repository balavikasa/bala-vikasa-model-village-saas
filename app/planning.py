from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from flask import Blueprint, jsonify, render_template, request, send_file
from flask_login import current_user, login_required

from .extensions import db
from .models import ActionPlan, ActionPlanType, AuditAction, Committee, Role
from .scoping import ScopeError, can_manage_action_plan, json_role_required, require_scoped
from .services.audit import model_snapshot, record_audit
from .services.monthly_plans import (
    PlanningError,
    action_plan_status,
    build_export_workbook,
    confirm_import,
    month_key,
    month_label,
    month_start,
    plan_locked,
    planning_rows,
    planning_summary,
    prepare_next_month,
    stage_import,
)
from .timeutils import current_month

bp = Blueprint("planning", __name__)


@bp.get("/action-plans")
@login_required
def action_plans_page():
    selected = month_start(request.args.get("month"))
    return render_template(
        "action_plans.html",
        selected_month=month_key(selected),
        selected_month_label=month_label(selected),
        can_manage=current_user.role in {Role.ADMIN, Role.PC},
        can_transfer=current_user.role in {Role.ADMIN, Role.PC, Role.PM},
    )


@bp.get("/action-plans/transfer")
@login_required
def action_plan_transfer_page():
    if current_user.role not in {Role.ADMIN, Role.PC, Role.PM}:
        return render_template("403.html"), 403
    selected = month_start(request.args.get("month"))
    return render_template(
        "action_plan_transfer.html",
        selected_month=month_key(selected),
        selected_month_label=month_label(selected),
        can_import=current_user.role in {Role.ADMIN, Role.PC},
    )


@bp.get("/api/v1/planning/month")
@login_required
def month_data():
    try:
        selected = month_start(request.args.get("month"))
        rows = planning_rows(current_user._get_current_object(), selected)
        return jsonify(
            month=month_key(selected),
            label=month_label(selected),
            rows=rows,
            summary=planning_summary(rows),
            can_manage=current_user.role in {Role.ADMIN, Role.PC},
        )
    except PlanningError as exc:
        return jsonify(error=str(exc)), 422


@bp.patch("/api/v1/planning/plans/<int:plan_id>")
@login_required
@json_role_required(Role.ADMIN, Role.PC)
def update_monthly_plan(plan_id: int):
    try:
        plan = require_scoped(ActionPlan, plan_id, current_user)
        if not can_manage_action_plan(current_user, plan.committee):
            raise ScopeError("You cannot change this monthly plan.")
        if plan_locked(plan):
            raise PlanningError("This monthly plan is locked by immutable history.")

        data = request.get_json(silent=True) or {}
        plan_type_raw = str(data.get("plan_type") or "").strip()
        assigned_raw = str(data.get("assigned_date") or "").strip()
        notes = str(data.get("notes") or "").strip() or None

        if assigned_raw and not plan_type_raw:
            raise PlanningError("Choose Attendance or Specials before assigning a date.")

        plan_type = ActionPlanType(plan_type_raw) if plan_type_raw else None
        assigned_date = None
        if assigned_raw:
            from datetime import date
            assigned_date = date.fromisoformat(assigned_raw)
            if not plan.plan_month or (assigned_date.year, assigned_date.month) != (
                plan.plan_month.year,
                plan.plan_month.month,
            ):
                raise PlanningError("Assigned Date must be inside the selected plan month.")

        before = model_snapshot(plan)
        plan.plan_type = plan_type
        plan.assigned_date = assigned_date
        plan.notes = notes
        plan.assigned_by_user_id = current_user.id
        record_audit(AuditAction.UPDATE, plan, before=before, after=model_snapshot(plan))
        db.session.commit()
        return jsonify(
            item={
                "id": plan.id,
                "plan_type": plan.plan_type.value if plan.plan_type else None,
                "assigned_date": plan.assigned_date.isoformat() if plan.assigned_date else None,
                "notes": plan.notes,
                "status": action_plan_status(plan),
                "locked": plan_locked(plan),
            }
        )
    except ScopeError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 403
    except (PlanningError, ValueError) as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422


@bp.post("/api/v1/planning/plans")
@login_required
@json_role_required(Role.ADMIN, Role.PC)
def create_monthly_plan():
    try:
        data = request.get_json(silent=True) or {}
        selected = month_start(data.get("month"))
        if selected < current_month():
            raise PlanningError("Past monthly history is immutable and cannot be created or changed.")
        committee = require_scoped(Committee, int(data.get("committee_id")), current_user)
        if not can_manage_action_plan(current_user, committee):
            raise ScopeError("You cannot assign a plan for that committee.")
        existing = db.session.scalar(
            db.select(ActionPlan).where(
                ActionPlan.committee_id == committee.id,
                ActionPlan.plan_month == selected,
                ActionPlan.is_deleted.is_(False),
            )
        )
        if existing:
            return jsonify(error="A monthly plan already exists for that committee."), 409

        plan_type_raw = str(data.get("plan_type") or "").strip()
        assigned_raw = str(data.get("assigned_date") or "").strip()
        if assigned_raw and not plan_type_raw:
            raise PlanningError("Choose Attendance or Specials before assigning a date.")
        plan_type = ActionPlanType(plan_type_raw) if plan_type_raw else None
        assigned = None
        if assigned_raw:
            from datetime import date
            assigned = date.fromisoformat(assigned_raw)
            if (assigned.year, assigned.month) != (selected.year, selected.month):
                raise PlanningError("Assigned Date must be inside the plan month.")

        plan = ActionPlan(
            committee_id=committee.id,
            title=committee.name,
            plan_month=selected,
            plan_type=plan_type,
            assigned_date=assigned,
            assigned_by_user_id=current_user.id,
            notes=str(data.get("notes") or "").strip() or None,
        )
        db.session.add(plan)
        db.session.flush()
        record_audit(AuditAction.CREATE, plan, after=model_snapshot(plan))
        db.session.commit()
        return jsonify(id=plan.id), 201
    except ScopeError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 403
    except (PlanningError, ValueError, TypeError) as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422


@bp.post("/api/v1/planning/prepare-next-month")
@login_required
@json_role_required(Role.ADMIN, Role.PC)
def prepare_next_month_route():
    try:
        source = month_start((request.get_json(silent=True) or {}).get("month"))
        result = prepare_next_month(current_user._get_current_object(), source)
        return jsonify(result)
    except PlanningError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422


@bp.get("/action-plans/export.xlsx")
@login_required
def export_month():
    if current_user.role not in {Role.ADMIN, Role.PC, Role.PM}:
        return jsonify(error="You do not have permission to export action plans."), 403
    try:
        selected = month_start(request.args.get("month"))
        workbook = build_export_workbook(current_user._get_current_object(), selected)
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return send_file(
            buffer,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"Action_Plans_{month_key(selected)}.xlsx",
        )
    except PlanningError as exc:
        return jsonify(error=str(exc)), 422


@bp.post("/api/v1/planning/import/preview")
@login_required
@json_role_required(Role.ADMIN, Role.PC)
def import_preview():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify(error="Choose an .xlsx action-plan workbook."), 422
    if not upload.filename.lower().endswith(".xlsx"):
        return jsonify(error="Only .xlsx action-plan workbooks are accepted."), 422
    try:
        selected = month_start(request.form.get("month"))
        # NamedTemporaryFile stays outside executable/static paths.
        with NamedTemporaryFile(suffix=".xlsx", delete=False) as handle:
            upload.save(handle)
            temp = Path(handle.name)
        try:
            token, preview = stage_import(temp, current_user._get_current_object(), selected)
        finally:
            temp.unlink(missing_ok=True)
        return jsonify(token=token, preview=preview)
    except PlanningError as exc:
        return jsonify(error=str(exc)), 422


@bp.post("/api/v1/planning/import/confirm")
@login_required
@json_role_required(Role.ADMIN, Role.PC)
def import_confirm():
    data = request.get_json(silent=True) or {}
    try:
        selected = month_start(data.get("month"))
        result = confirm_import(
            str(data.get("token") or ""),
            current_user._get_current_object(),
            selected,
        )
        return jsonify(result)
    except PlanningError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422
