from __future__ import annotations

from io import BytesIO

from flask import Blueprint, Response, jsonify, render_template, request, send_file
from flask_login import current_user, login_required

from .reporting_exports import coverage_csv, coverage_workbook
from .services.coverage import coverage_map, coverage_report

bp = Blueprint('coverage', __name__)


@bp.get('/coverage')
@login_required
def page():
    return render_template('coverage.html')


@bp.get('/api/v1/coverage')
@login_required
def data():
    try:
        result = coverage_report(current_user._get_current_object(), request.args)
        result['map_items'] = coverage_map(result)
        result.pop('all_items')
        result.pop('coverage_rows')
        result.pop('all_submissions')
        return jsonify(result)
    except ValueError as exc:
        return jsonify(error=str(exc)), 422


@bp.get('/coverage/export.xlsx')
@login_required
def excel():
    try:
        result = coverage_report(current_user._get_current_object(), request.args)
        buffer = BytesIO()
        coverage_workbook(result).save(buffer)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True,
                         download_name=f"Bala_Vikasa_Coverage_{result['period']['to']}_{result['filters_applied']['status']}.xlsx",
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except ValueError as exc:
        return jsonify(error=str(exc)), 422


@bp.get('/coverage/export.csv')
@login_required
def csv_export():
    try:
        result = coverage_report(current_user._get_current_object(), request.args)
        response = Response('\ufeff' + coverage_csv(result), mimetype='text/csv')
        response.headers['Content-Disposition'] = 'attachment; filename=Bala_Vikasa_Village_Coverage.csv'
        return response
    except ValueError as exc:
        return jsonify(error=str(exc)), 422


@bp.after_request
def private_report(response):
    response.headers['Cache-Control'] = 'private, no-store'
    return response
