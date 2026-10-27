from __future__ import annotations

from io import BytesIO

from flask import Blueprint, current_app, jsonify, render_template, request, send_file
from flask_login import current_user, login_required

from .extensions import db
from .models import ActionPlan, Role, VillageAttendanceVisit, AttendanceEntry
from .scoping import ScopeError, require_scoped
from .services.audit import soft_delete
from .services.monthly_plans import PlanningError, month_key, month_label, month_start
from .services.reports import (
    export_report_workbook,
    report_detail,
    report_rows,
    report_summary,
)

bp = Blueprint("reports", __name__)


@bp.get("/reports")
@login_required
def reports_page():
    selected = month_start(request.args.get("month"))
    return render_template(
        "reports.html",
        selected_month=month_key(selected),
        selected_month_label=month_label(selected),
    )


@bp.get("/reports/village/<int:visit_id>")
@login_required
def village_report(visit_id: int):
    try:
        visit = require_scoped(VillageAttendanceVisit, visit_id, current_user)
    except ScopeError:
        return ("Not found", 404)
    entries = [entry for entry in visit.entries if entry.is_enabled and not entry.is_deleted]
    entries.sort(key=lambda entry: entry.committee.name.casefold())
    if not entries:
        return ("No active attendance for this visit", 404)
    return render_template("village_attendance_report.html", visit=visit, entries=entries)


@bp.get("/reports/plan/<int:plan_id>")
@login_required
def report_detail_page(plan_id: int):
    try:
        plan = require_scoped(ActionPlan, plan_id, current_user)
        # Touch full relationship graph while the request session is active.
        detail = report_detail(plan)
        return render_template("report_detail.html", detail=detail)
    except ScopeError:
        return ("Not found", 404)


@bp.get("/api/v1/reports")
@login_required
def report_data():
    try:
        selected = month_start(request.args.get("month"))
        plan_type = (request.args.get("type") or "").strip() or None
        status = (request.args.get("status") or "").strip() or None
        if plan_type not in {None, "Attendance", "Specials"}:
            raise PlanningError("Type must be Attendance or Specials.")
        rows = report_rows(current_user._get_current_object(), selected, plan_type=plan_type, status=status)
        return jsonify(
            month=month_key(selected),
            label=month_label(selected),
            items=rows,
            summary=report_summary(rows),
        )
    except (PlanningError, ValueError) as exc:
        return jsonify(error=str(exc)), 422


@bp.delete("/api/v1/reports/village/<int:visit_id>")
@login_required
def delete_village_report(visit_id: int):
    if current_user.role != Role.ADMIN:
        return jsonify(error="Administrator access required."), 403
    try:
        visit = require_scoped(VillageAttendanceVisit, visit_id, current_user)
    except ScopeError:
        return jsonify(error="Report not found."), 404
    actor = current_user._get_current_object()
    retention = current_app.config["RECYCLE_RETENTION_DAYS"]
    try:
        for entry in visit.entries:
            if not entry.is_deleted:
                soft_delete(entry, actor, retention)
                if not entry.action_plan.is_deleted:
                    soft_delete(entry.action_plan, actor, retention)
        soft_delete(visit, actor, retention)
        db.session.commit()
        return jsonify(ok=True, message="All committee reports moved to Recycle Bin."), 200
    except Exception:
        db.session.rollback()
        raise


@bp.delete("/api/v1/reports/plan/<int:plan_id>")
@login_required
def delete_report_plan(plan_id: int):
    if current_user.role != Role.ADMIN:
        return jsonify(error="Administrator access required."), 403

    try:
        plan = require_scoped(ActionPlan, plan_id, current_user)
    except ScopeError:
        return jsonify(error="Report not found."), 404

    recycle_ids: list[int] = []
    actor = current_user._get_current_object()
    retention = current_app.config["RECYCLE_RETENTION_DAYS"]

    entry = None
    if plan.attendance_entry is not None and not plan.attendance_entry.is_deleted:
        entry = plan.attendance_entry
    elif plan.specials_entry is not None and not plan.specials_entry.is_deleted:
        entry = plan.specials_entry

    try:
        if entry is not None:
            row = soft_delete(entry, actor, retention)
            recycle_ids.append(row.id)

        row = soft_delete(plan, actor, retention)
        recycle_ids.append(row.id)
        db.session.commit()
        return jsonify(
            ok=True,
            recycle_bin_ids=recycle_ids,
            message="Report moved to the Recycle Bin.",
        )
    except Exception:
        db.session.rollback()
        raise


@bp.get("/reports/export.xlsx")
@login_required
def export_reports():
    try:
        selected = month_start(request.args.get("month"))
        plan_type = (request.args.get("type") or "").strip() or None
        status = (request.args.get("status") or "").strip() or None
        if plan_type not in {None, "Attendance", "Specials"}:
            raise PlanningError("Type must be Attendance or Specials.")
        workbook = export_report_workbook(
            current_user._get_current_object(),
            selected,
            plan_type=plan_type,
            status=status,
        )
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        suffix = f"_{plan_type}" if plan_type else ""
        return send_file(
            buffer,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"Model_Village_Reports_{month_key(selected)}{suffix}.xlsx",
        )
    except (PlanningError, ValueError) as exc:
        return jsonify(error=str(exc)), 422
