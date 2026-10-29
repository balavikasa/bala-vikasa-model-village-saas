from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import (
    DA,
    ActionPlan,
    Committee,
    User,
    Village,
)
from ..scoping import scoped_select
from ..timeutils import current_month, local_today


def action_plan_status(plan: ActionPlan, today: date | None = None) -> str:
    today = today or local_today()
    if plan.attendance_entry and not plan.attendance_entry.is_deleted:
        return plan.attendance_entry.status.value
    if plan.specials_entry and not plan.specials_entry.is_deleted:
        return plan.specials_entry.status.value if plan.specials_entry.status else "Completed"
    if not plan.is_executable:
        return "Draft"
    if plan.assigned_date < today:
        return "Failure"
    if plan.assigned_date == today:
        return "Due today"
    return "Scheduled"


def scoped_action_plans(user: User, month: date | None = None) -> list[ActionPlan]:
    selected_month = (month or current_month()).replace(day=1)
    stmt = (
        scoped_select(ActionPlan, user)
        .where(ActionPlan.plan_month == selected_month)
        .options(
            selectinload(ActionPlan.attendance_entry),
            selectinload(ActionPlan.specials_entry),
            selectinload(ActionPlan.committee)
            .selectinload(Committee.village)
            .selectinload(Village.da)
            .selectinload(DA.pc),
        )
        .order_by(ActionPlan.assigned_date.asc().nullslast(), ActionPlan.id)
    )
    return list(db.session.scalars(stmt).unique())


def dashboard_summary(user: User, params=None) -> dict[str, Any]:
    from .coverage import coverage_report
    result = coverage_report(user, params)
    return _coverage_summary(result)


def _coverage_summary(result: dict[str, Any]) -> dict[str, Any]:
    c = result['counts']
    return {
        'counts': {**c, 'attendance_entries': c['committees_recorded'],
                   'action_plans': 0, 'specials_entries': 0, 'participants': 0},
        'period': result['period'], 'current_month': result['current_month'],
        'status_breakdown': {'Done': c['villages_done'], 'Not done': c['villages_pending']},
        'cluster_breakdown': {r['name']: r['total'] for r in result['clusters']},
        'gender_distribution': {'Male': c['male'], 'Female': c['female']},
    }


def map_markers(user: User, params=None) -> list[dict[str, Any]]:
    from .coverage import coverage_map, coverage_report
    result = coverage_report(user, params)
    return coverage_map(result, include_other=result['filters_applied']['status'] == 'all')


def dashboard_series(user: User, params=None) -> dict[str, Any]:
    from .coverage import coverage_report
    result = coverage_report(user, params)
    return {**_coverage_summary(result), 'daily_trend': [
        {**r, 'label': r['date']} for r in result['trend']],
        'granularity': result['granularity'],
        'committee_aggregates': result['committees'],
        'status_by_cluster': {r['name']: {'Done': r['done'], 'Not done': r['pending']}
                              for r in result['clusters']}}


def recent_village_activity(user: User, params=None) -> dict[str, Any]:
    from .coverage import coverage_report
    result = coverage_report(user, params)
    recent = [{'id': v['id'], 'village': v['village'], 'date': v['date'],
               'people': v['people_attended'], 'outside_assignment': v['other_village'],
               'report_url': v['view_url']} for v in result['all_submissions'][:6]]
    pending = [{'id': r['id'], 'name': r['name'], 'url': f"/directory/village/{r['id']}"}
               for r in result['coverage_rows'] if r['in_scope'] and r['status'] == 'Pending']
    return {'period': result['period'], 'recent': recent, 'pending': pending[:8],
            'pending_total': len(pending)}
