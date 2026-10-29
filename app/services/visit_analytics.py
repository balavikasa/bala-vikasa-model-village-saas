"""Analytics consumes the same role-scoped, period-filtered coverage contract."""
from __future__ import annotations

from typing import Any

from ..models import User
from .coverage import coverage_map, coverage_report


def visit_analytics(user: User, month: str | None = None, *, cluster: str = '',
                    da_id: int | None = None, village_id: int | None = None,
                    committee_type: str = '', params=None) -> dict[str, Any]:
    args = dict(params or {})
    for key, value in [('month', month), ('cluster', cluster), ('da', da_id),
                       ('village', village_id), ('committee', committee_type)]:
        if value is not None and value != '':
            args.setdefault(key, value)
    result = coverage_report(user, args)
    c = result['counts']
    return {'month': result['period']['to'][:7], 'period': result['period'],
            'scope': 'actual-village-visits', 'filters': result['options'],
            'counts': c, 'gender': {'Male': c['male'], 'Female': c['female']},
            'committees': result['committees'], 'clusters': result['clusters'],
            'das': [{'name': r['name'], 'villages': r['done'], 'people': r['people_attended'],
                     'visits': r['visits'], 'assigned': r['assigned'], 'pending': r['pending'],
                     'other_visits': r['other_visits']} for r in result['team']],
            'team': result['team'], 'trend': result['trend'], 'granularity': result['granularity'],
            'pending': [r for r in result['coverage_rows'] if r['in_scope'] and r['status'] == 'Pending'],
            'map_items': coverage_map(result), 'monthly_coverage': result['monthly_coverage']}
