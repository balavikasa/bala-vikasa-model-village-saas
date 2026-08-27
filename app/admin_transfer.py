from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from flask import Blueprint, jsonify, render_template, request, send_file
from flask_login import current_user, login_required

from .extensions import db
from .models import Role
from .scoping import json_role_required, role_required
from .services.master_transfer import (
    MasterTransferError,
    build_export_workbook,
    confirm_import,
    resource_catalog,
    stage_import,
)

bp = Blueprint("admin_transfer", __name__)


@bp.get("/admin/data-transfer")
@login_required
@role_required(Role.ADMIN, Role.PC)
def page():
    return render_template(
        "admin_transfer.html",
        resources=resource_catalog(current_user._get_current_object()),
    )


@bp.get("/admin/data-transfer/export.xlsx")
@login_required
@role_required(Role.ADMIN, Role.PC)
def export_master():
    resource = (request.args.get("resource") or "").strip()

    try:
        workbook = build_export_workbook(
            resource,
            current_user._get_current_object(),
        )

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            as_attachment=True,
            download_name=f"Model_Village_{resource}_master.xlsx",
        )

    except MasterTransferError as exc:
        return jsonify(error=str(exc)), 422


@bp.post("/api/v1/admin/data-transfer/preview")
@login_required
@json_role_required(Role.ADMIN, Role.PC)
def preview():
    resource = (request.form.get("resource") or "").strip()
    upload = request.files.get("file")

    if not upload or not upload.filename:
        return jsonify(error="Choose an .xlsx workbook."), 422

    if not upload.filename.lower().endswith(".xlsx"):
        return jsonify(error="Only .xlsx workbooks are accepted."), 422

    try:
        with NamedTemporaryFile(suffix=".xlsx", delete=False) as handle:
            upload.save(handle)
            temp = Path(handle.name)

        try:
            token, result = stage_import(
                temp,
                resource,
                current_user._get_current_object(),
            )
        finally:
            temp.unlink(missing_ok=True)

        return jsonify(
            token=token,
            preview=result,
        )

    except MasterTransferError as exc:
        return jsonify(error=str(exc)), 422


@bp.post("/api/v1/admin/data-transfer/confirm")
@login_required
@json_role_required(Role.ADMIN, Role.PC)
def confirm():
    data = request.get_json(silent=True) or {}

    try:
        result = confirm_import(
            str(data.get("token") or ""),
            str(data.get("resource") or ""),
            current_user._get_current_object(),
        )

        return jsonify(result)

    except MasterTransferError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 422