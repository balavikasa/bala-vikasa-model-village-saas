"""Calendar periods and coverage calculations, independent of the web framework.

Authorization is performed by the SQLAlchemy adapter before data enters this module.
A completed active village submission establishes coverage; standalone legacy committee
entries are deliberately not promoted to completed village visits.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class ReportingPeriod:
    start: date | None
    end: date  # inclusive; dates are already application-local entry dates
    key: str
    label: str

    def contains(self, value: str | date) -> bool:
        day = date.fromisoformat(value) if isinstance(value, str) else value
        return (self.start is None or day >= self.start) and day <= self.end

    def as_dict(self) -> dict[str, Any]:
        return {'key': self.key, 'label': self.label,
                'from': self.start.isoformat() if self.start else None,
                'to': self.end.isoformat(), 'timezone': 'Asia/Kolkata',
                'week_start': 'Monday', 'date_basis': 'server-local accepted entry date'}


def month_after(value: date) -> date:
    return date(value.year + (value.month == 12), value.month % 12 + 1, 1)


def resolve_period(params: Mapping[str, Any], today: date) -> ReportingPeriod:
    """Resolve presets without relying on the browser clock or timezone."""
    key = str(params.get('period') or ('month' if params.get('month') else 'this_month'))
    start = today
    end = today
    labels = {'today': 'Today', 'yesterday': 'Yesterday', 'this_week': 'This week',
              'last_week': 'Last week', 'this_month': 'This month', 'last_month': 'Last month',
              'this_year': 'This year', 'last_year': 'Last year', 'all': 'All time'}
    try:
        if key == 'today':
            pass
        elif key == 'yesterday':
            start = end = today - timedelta(days=1)
        elif key in {'day', 'week'}:
            start = date.fromisoformat(str(params.get('date') or ''))
            if key == 'week':
                start -= timedelta(days=start.weekday())
                end = start + timedelta(days=6)
            else:
                end = start
        elif key in {'this_week', 'last_week'}:
            start = today - timedelta(days=today.weekday() + (7 if key == 'last_week' else 0))
            end = start + timedelta(days=6)
        elif key in {'month', 'this_month', 'last_month'}:
            if key == 'month':
                raw = str(params.get('month') or '')
                if len(raw) != 7:
                    raise ValueError('Select a month using YYYY-MM.')
                start = date.fromisoformat(raw + '-01')
            else:
                start = today.replace(day=1)
                if key == 'last_month':
                    start = (start - timedelta(days=1)).replace(day=1)
            end = month_after(start) - timedelta(days=1)
        elif key in {'year', 'this_year', 'last_year'}:
            year = int(params.get('year') or today.year) if key == 'year' else today.year - (key == 'last_year')
            start, end = date(year, 1, 1), date(year, 12, 31)
        elif key == 'custom':
            start = date.fromisoformat(str(params.get('from') or ''))
            end = date.fromisoformat(str(params.get('to') or ''))
        elif key == 'all':
            start, end = None, today
        else:
            raise ValueError('Unknown reporting period.')
        if start and start > end:
            raise ValueError('From date must be on or before To date.')
        if (start and not 2000 <= start.year <= 2100) or not 2000 <= end.year <= 2100:
            raise ValueError('Reporting dates must be between 2000 and 2100.')
    except (TypeError, OverflowError, ValueError) as exc:
        raise ValueError(f'Invalid reporting dates: {exc}') from exc
    display = 'All time' if start is None else start.strftime('%d %b %Y') if start == end else f'{start:%d %b %Y} - {end:%d %b %Y}'
    return ReportingPeriod(start, end, key, f'{labels[key]} ({display})' if key in labels and key != 'all' else display)


def parse_filters(params: Mapping[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key in ('pc', 'da', 'submitted_da', 'village'):
        raw = params.get(key)
        if raw in (None, ''):
            values[key] = None
        else:
            try:
                values[key] = int(str(raw))
                if values[key] <= 0:
                    raise ValueError()
            except (TypeError, ValueError) as exc:
                raise ValueError(f'{key} must be a positive record ID.') from exc
    values.update(cluster=str(params.get('cluster') or '').strip(),
                  committee=str(params.get('committee') or '').strip(),
                  q=str(params.get('q') or '').strip()[:200],
                  status=str(params.get('status') or 'all').lower())
    if values['status'] not in {'all', 'done', 'pending', 'other'}:
        raise ValueError('Status must be all, done, pending or other.')
    for key, default, maximum in [('page', 1, 1000000), ('page_size', 25, 100)]:
        try:
            values[key] = int(params.get(key) or default)
            if not 1 <= values[key] <= maximum:
                raise ValueError()
        except (TypeError, ValueError) as exc:
            raise ValueError(f'{key} is out of range.') from exc
    return values


def active(row: Mapping[str, Any]) -> bool:
    return bool(row.get('is_enabled', True)) and not row.get('is_deleted', False)


def _sum_visits(rows: list[dict[str, Any]]) -> dict[str, int]:
    male = sum(v['male'] for v in rows)
    female = sum(v['female'] for v in rows)
    return {'visits': len(rows), 'male': male, 'female': female,
            'people_attended': male + female,
            'new_members': sum(v['new_members'] for v in rows),
            'committees_recorded': sum(v['committees_recorded'] for v in rows)}


def build_coverage(villages: list[dict[str, Any]], visits: list[dict[str, Any]],
                   team: list[dict[str, Any]], period: ReportingPeriod,
                   filters: dict[str, Any], today: date) -> dict[str, Any]:
    """Return a complete, deterministic report; paginate only its rendered rows.

    Main coverage is current in-scope active villages. A DA's own outside-assignment
    visits are separate, never inflating their assigned denominator. Attendance
    counts are instances across committees, never guessed unique-person counts.
    """
    # Filter the village universe independently of visit existence: zero-activity
    # villages must survive the query so Pending is a genuine complement.
    q = filters['q'].casefold()
    candidates = []
    for v in villages:
        if not active(v):
            continue
        if any(filters[k] is not None and filters[k] != v[field]
               for k, field in [('pc', 'pc_id'), ('da', 'assigned_da_id'), ('village', 'id')]):
            continue
        if filters['cluster'] and filters['cluster'] != v['cluster']:
            continue
        if filters['committee'] and filters['committee'] not in v.get('committee_types', []):
            continue
        if q and q not in ' '.join(str(v.get(k) or '') for k in ('name', 'cluster', 'pc', 'assigned_da', 'mandal', 'district')).casefold():
            continue
        candidates.append(v)
    lookup = {v['id']: v for v in candidates}
    universe = {v['id'] for v in candidates if v.get('in_scope', True)}
    normalized = []
    seen_visits = set()
    for v in visits:
        if not active(v) or v['id'] in seen_visits or v['village_id'] not in lookup:
            continue
        if filters['submitted_da'] is not None and v.get('submitted_da_id') != filters['submitted_da']:
            continue
        entries = [e for e in v.get('entries', []) if active(e) and
                   (not filters['committee'] or filters['committee'] == e.get('committee_type'))]
        if not entries:
            continue
        seen_visits.add(v['id'])
        n = {**v, 'entries': entries, 'male': sum(int(e.get('male') or 0) for e in entries),
             'female': sum(int(e.get('female') or 0) for e in entries),
             'new_members': int(v.get('new_members') or 0),
             'committees_recorded': len(entries)}
        n['people_attended'] = n['male'] + n['female']
        normalized.append(n)
    current = [v for v in normalized if period.contains(v['date'])]
    current.sort(key=lambda v: (v['date'], v['id']), reverse=True)
    by_village: dict[int, list[dict[str, Any]]] = defaultdict(list)
    history: dict[int, list[str]] = defaultdict(list)
    for v in normalized:
        if date.fromisoformat(v['date']) <= today:
            history[v['village_id']].append(v['date'])
    for v in current:
        by_village[v['village_id']].append(v)
    done_ids = universe & set(by_village)
    outside_ids = set(by_village) - universe
    scope_visits = [v for v in current if v['village_id'] in universe]
    outside_visits = [v for v in current if v['village_id'] not in universe]
    counts = {'villages': len(universe), 'villages_done': len(done_ids),
              'villages_pending': len(universe - done_ids), **_sum_visits(scope_visits),
              'other_villages_visited': len(outside_ids),
              'other_people_attended': sum(v['people_attended'] for v in outside_visits)}

    rows = []
    for v in sorted(candidates, key=lambda r: (r['name'].casefold(), r['id'])):
        rows_for_village = by_village.get(v['id'], [])
        if v['id'] not in universe and not rows_for_village:
            continue
        latest = rows_for_village[0] if rows_for_village else None
        totals = _sum_visits(rows_for_village)
        rows.append({**{k: v.get(k) for k in ('id', 'name', 'cluster', 'pc_id', 'pc',
                    'assigned_da_id', 'assigned_da', 'latitude', 'longitude', 'mandal', 'district', 'committee_count')},
                     'in_scope': v['id'] in universe,
                     'status': 'Done' if latest else 'Pending',
                     'visit_date': latest['date'] if latest else None,
                     'last_visit': max(history.get(v['id'], []), default=None),
                     'submitted_by': ', '.join(dict.fromkeys(r['submitted_by'] for r in rows_for_village)),
                     'report_url': f"/reports/village/{latest['id']}" if latest else None,
                     'latest_visit_id': latest['id'] if latest else None,
                     **{k: val if rows_for_village else None for k, val in totals.items()}})
    status = filters['status']
    selected = [r for r in rows if (not r['in_scope'] if status == 'other' else
                r['in_scope'] and (status == 'all' or r['status'].lower() == status))]
    selected_ids = {r['id'] for r in selected}
    selected_visits = [v for v in current if v['village_id'] in selected_ids]
    selection_counts = {'villages': len(selected), **_sum_visits(selected_visits)}
    start_index = (filters['page'] - 1) * filters['page_size']

    # Coverage responsibility and actual work performed are deliberately different
    # columns; include active DAs even when they submitted nothing.
    team_rows = []
    for da in sorted(team, key=lambda r: r['name'].casefold()):
        if not active(da):
            continue
        if filters['pc'] is not None and da['pc_id'] != filters['pc']:
            continue
        if filters['da'] is not None and da['id'] != filters['da']:
            continue
        if filters['submitted_da'] is not None and da['id'] != filters['submitted_da']:
            continue
        if filters['cluster'] and da['cluster'] != filters['cluster']:
            continue
        owned = {v['id'] for v in candidates if v['id'] in universe and v['assigned_da_id'] == da['id']}
        work = [v for v in current if v.get('submitted_da_id') == da['id']]
        team_rows.append({**da, 'assigned': len(owned), 'done': len(owned & done_ids),
                          'pending': len(owned - done_ids), **_sum_visits(work),
                          'other_visits': sum(lookup[v['village_id']]['assigned_da_id'] != da['id'] for v in work)})
    clusters = []
    for cluster in sorted({v['cluster'] for v in candidates if v['id'] in universe}):
        ids = {v['id'] for v in candidates if v['id'] in universe and v['cluster'] == cluster}
        clusters.append({'name': cluster, 'total': len(ids), 'done': len(ids & done_ids),
                         'pending': len(ids - done_ids)})

    # For an all-time selection begin at first recorded evidence, not an arbitrary
    # past year. Monthly snapshots never infer an obligation from one annual visit.
    first = period.start or min((date.fromisoformat(v['date']) for v in normalized), default=today)
    monthly_coverage = []
    cursor = first.replace(day=1)
    while cursor <= period.end:
        end_month = month_after(cursor) - timedelta(days=1)
        ids = {v['village_id'] for v in current if cursor <= date.fromisoformat(v['date']) <= end_month}
        monthly_coverage.append({'month': cursor.strftime('%Y-%m'), 'villages': len(universe),
                                 'done': len(ids & universe), 'pending': len(universe - ids)})
        cursor = month_after(cursor)
    span = (period.end - first).days
    granularity = 'day' if span <= 31 else 'week' if span <= 120 else 'month'
    buckets: dict[str, dict[str, Any]] = {}
    cursor = first
    while cursor <= period.end:
        key_date = cursor if granularity == 'day' else cursor - timedelta(days=cursor.weekday()) if granularity == 'week' else cursor.replace(day=1)
        key = key_date.isoformat()
        if key not in buckets:
            buckets[key] = {'month': key, 'date': key, 'visits': 0, 'people': 0, 'villages': set()}
        cursor = month_after(cursor) if granularity == 'month' else cursor + timedelta(days=1)
    for v in scope_visits:
        day = date.fromisoformat(v['date'])
        key_date = day if granularity == 'day' else day - timedelta(days=day.weekday()) if granularity == 'week' else day.replace(day=1)
        bucket = buckets.get(key_date.isoformat())
        if bucket is not None:
            bucket['visits'] += 1
            bucket['people'] += v['people_attended']
            bucket['villages'].add(v['village_id'])
    trend = [{**b, 'villages': len(b['villages'])} for b in buckets.values()]
    committees: Counter[str] = Counter()
    for v in scope_visits:
        for e in v['entries']:
            committees[e.get('committee_type') or e.get('committee') or 'Other'] += int(e.get('male') or 0) + int(e.get('female') or 0)

    submissions = []
    for v in current:
        owner = lookup[v['village_id']]
        submissions.append({k: val for k, val in {**v, 'village': owner['name'],
                 'cluster': owner['cluster'], 'pc': owner['pc'], 'assigned_da': owner['assigned_da'],
                 'other_village': v.get('submitted_da_id') != owner['assigned_da_id'],
                 'view_url': f"/reports/village/{v['id']}"}.items() if k != 'entries'})
    month_start = today.replace(day=1)
    this_month_done = {v['village_id'] for v in normalized if month_start <= date.fromisoformat(v['date']) <= today} & universe
    return {'period': period.as_dict(), 'filters_applied': filters, 'counts': counts,
            'selection_counts': selection_counts, 'total': len(selected),
            'page': filters['page'], 'page_size': filters['page_size'],
            'pages': max(1, (len(selected) + filters['page_size'] - 1) // filters['page_size']),
            'items': selected[start_index:start_index + filters['page_size']],
            'all_items': selected, 'coverage_rows': rows,
            'all_submissions': submissions,
            'submissions': [v for v in submissions if v['village_id'] in selected_ids],
            'team': team_rows, 'clusters': clusters, 'committees': dict(committees),
            'trend': trend, 'granularity': granularity, 'monthly_coverage': monthly_coverage,
            'current_month': {'month': today.strftime('%Y-%m'), 'done': len(this_month_done),
                              'pending': len(universe - this_month_done)},
            'definitions': {
                'coverage': 'Active village submissions; standalone legacy committee attendance is historical only.',
                'pending': 'Not visited in the selected period; this does not mean overdue.',
                'people': 'Committee attendance instances, not unique people across committees or dates.',
                'new_members': 'Village-wide totals; not added to registered-member attendance.',
                'assignments': 'Coverage uses current active village assignments, not historical assignment snapshots.',
                'submitter': 'When Submitted by DA is selected, Done means recorded by that DA within your scope.'}}
