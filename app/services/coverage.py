"""Read-only reporting adapter; scope is enforced before aggregation or export."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import DA, AttendanceEntry, User, Village, VillageAttendanceVisit
from ..reporting_core import build_coverage, parse_filters, resolve_period
from ..scoping import scoped_select
from ..timeutils import local_today


def coverage_report(user: User, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
    args = params or {}
    today = local_today()
    period = resolve_period(args, today)
    filters = parse_filters(args)
    assigned = list(db.session.scalars(
        scoped_select(Village, user).where(Village.is_enabled.is_(True), Village.is_deleted.is_(False))
        .options(selectinload(Village.da).selectinload(DA.pc), selectinload(Village.committees))
    ).unique())
    assigned_ids = {v.id for v in assigned}
    # No recent-feed limit: historical last-visit metadata, range totals and monthly
    # coverage must not depend on how many items the dashboard chooses to display.
    parents = list(db.session.scalars(
        scoped_select(VillageAttendanceVisit, user)
        .where(VillageAttendanceVisit.is_enabled.is_(True), VillageAttendanceVisit.is_deleted.is_(False))
        .options(selectinload(VillageAttendanceVisit.village).selectinload(Village.da).selectinload(DA.pc),
                 selectinload(VillageAttendanceVisit.village).selectinload(Village.committees),
                 selectinload(VillageAttendanceVisit.entries).selectinload(AttendanceEntry.committee))
    ).unique())
    parents = [v for v in parents if v.village.is_enabled and not v.village.is_deleted]
    village_models = {v.id: v for v in assigned}
    for visit in parents:
        # scoped_select grants a DA only their own visits outside assignment, not
        # another DA's submissions from the same external village.
        village_models.setdefault(visit.village_id, visit.village)
    villages = []
    for v in village_models.values():
        villages.append({'id': v.id, 'name': v.name, 'cluster': v.da.pc.cluster.value,
                         'pc_id': v.da.pc_id, 'pc': v.da.pc.full_name,
                         'assigned_da_id': v.da_id, 'assigned_da': v.da.full_name,
                         'in_scope': v.id in assigned_ids, 'latitude': v.latitude, 'longitude': v.longitude,
                         'mandal': v.mandal, 'district': v.district,
                         'committee_types': sorted({c.committee_type or c.name for c in v.committees
                                                   if c.is_enabled and not c.is_deleted}),
                         'committee_count': sum(c.is_enabled and not c.is_deleted for c in v.committees)})
    actor_ids = {v.submitted_by_user_id for v in parents}
    actors = {a.id: a for a in db.session.scalars(db.select(User).where(User.id.in_(actor_ids)))} if actor_ids else {}
    visits = []
    for v in parents:
        actor = actors.get(v.submitted_by_user_id)
        entries = [e for e in v.entries if e.is_enabled and not e.is_deleted]
        visits.append({'id': v.id, 'village_id': v.village_id, 'date': v.visit_date.isoformat(),
                       'submitted_da_id': actor.da_id if actor else None,
                       'submitted_by_user_id': v.submitted_by_user_id,
                       'submitted_by': actor.display_name if actor else 'Historical user',
                       'new_members': v.new_members_count if v.visit_month is not None
                                      else sum(e.new_members_count for e in entries),
                       'latitude': v.latitude, 'longitude': v.longitude,
                       'photo_url': f'/api/v1/photos/attendance/{entries[0].id}' if entries else None,
                       'entries': [{'male': e.male_count, 'female': e.female_count,
                                    'committee': e.committee.name,
                                    'committee_type': e.committee.committee_type or e.committee.name}
                                   for e in entries]})
    da_models = list(db.session.scalars(scoped_select(DA, user).where(
        DA.is_enabled.is_(True), DA.is_deleted.is_(False)).options(selectinload(DA.pc))))
    team = [{'id': d.id, 'name': d.full_name, 'pc_id': d.pc_id, 'pc': d.pc.full_name,
             'cluster': d.pc.cluster.value} for d in da_models]
    result = build_coverage(villages, visits, team, period, filters, today)
    option_villages = [v for v in villages if v['in_scope']]
    # Options contain only staff/identifiers represented in the authorized dataset.
    submitting = {d['id']: d['name'] for d in team}
    for v in visits:
        if v['submitted_da_id'] is not None:
            submitting[v['submitted_da_id']] = v['submitted_by']
    result['counts']['committees'] = sum(v['committee_count'] for v in villages if v['in_scope'] and v['id'] in {r['id'] for r in result['coverage_rows']})
    result['options'] = {
        'clusters': sorted({v['cluster'] for v in option_villages}),
        'pcs': [{'id': id_, 'name': name} for id_, name in sorted({v['pc_id']: v['pc'] for v in option_villages}.items())],
        'das': [{'id': d['id'], 'name': d['name']} for d in team],
        'submitters': [{'id': id_, 'name': name} for id_, name in sorted(submitting.items(), key=lambda item: item[1])],
        'villages': [{'id': v['id'], 'name': v['name']} for v in sorted(villages, key=lambda r: r['name'])],
        'committees': sorted({c for v in option_villages for c in v['committee_types']})}
    filtered_ids = {r['id'] for r in result['coverage_rows']}
    legacy = scoped_select(AttendanceEntry, user).where(
        AttendanceEntry.village_visit_id.is_(None), AttendanceEntry.is_enabled.is_(True),
        AttendanceEntry.is_deleted.is_(False), AttendanceEntry.village_id.in_(filtered_ids),
        AttendanceEntry.visit_date <= period.end)
    if period.start:
        legacy = legacy.where(AttendanceEntry.visit_date >= period.start)
    if filters['submitted_da'] is not None:
        legacy = legacy.where(AttendanceEntry.submitted_by_user_id.in_(
            db.select(User.id).where(User.da_id == filters['submitted_da'])))
    result['legacy_committee_records'] = db.session.scalar(
        db.select(func.count()).select_from(legacy.subquery())) or 0
    return result


def coverage_map(result: dict[str, Any], *, include_other: bool = False) -> list[dict[str, Any]]:
    """Map status and selected villages match the same period and filters."""
    by_village = {}
    for visit in result['all_submissions']:
        by_village.setdefault(visit['village_id'], visit)
    items = []
    for row in (result['coverage_rows'] if include_other else result['all_items']):
        visit = by_village.get(row['id'])
        lat = visit.get('latitude') if visit else row['latitude']
        lon = visit.get('longitude') if visit else row['longitude']
        items.append({'id': row['id'], 'name': row['name'], 'cluster': row['cluster'],
                      'da_name': row['assigned_da'], 'status': 'Visited' if row['status'] == 'Done' else 'Not visited',
                      'latitude': lat, 'longitude': lon,
                      'location_source': 'field-evidence' if visit else 'village-master',
                      'last_visit_date': row['visit_date'] or row['last_visit'],
                      'photo_url': visit.get('photo_url') if visit else None,
                      'outside_assignment': not row['in_scope'],
                      'committee_count': row.get('committee_count') or 0,
                      'report_url': row['report_url']})
    return items
