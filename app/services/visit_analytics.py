"""Role-scoped, DA-led visit analytics for the Bala Vikasa dashboard.

All metrics come from active VillageAttendanceVisit / AttendanceEntry rows.
Historical action plans and Specials are intentionally excluded.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any

from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import AttendanceEntry, DA, User, Village, VillageAttendanceVisit
from ..scoping import scoped_select
from ..timeutils import current_month


def _move_month(source: date, count: int) -> date:
    index = (source.year * 12 + source.month - 1) + count
    return date(index // 12, index % 12 + 1, 1)


def visit_analytics(user: User, month: str | None = None, *,
                    cluster: str = '', da_id: int | None = None,
                    village_id: int | None = None, committee_type: str = '') -> dict[str, Any]:
    """Server-enforced visibility plus optional filters (never expand role scope)."""
    if month:
        try:
            year, m = (int(value) for value in month.split('-'))
            if not (2020 <= year <= 2100 and 1 <= m <= 12):
                raise ValueError('Month is out of range')
            chosen = date(year, m, 1)
        except (ValueError, TypeError) as error:
            raise ValueError('Month must use YYYY-MM') from error
    else:
        chosen = current_month()
    cutoff = _move_month(chosen, 1)
    start = _move_month(chosen, -5)

    villages = list(db.session.scalars(
        scoped_select(Village, user)
        .options(selectinload(Village.da).selectinload(DA.pc),
                 selectinload(Village.committees))
        .order_by(Village.name)
    ).unique().all())
    villages = [v for v in villages if v.is_enabled and not v.is_deleted]
    filters = {
        'clusters': sorted({v.da.pc.cluster.value for v in villages}),
        'das': [{'id': da.id, 'name': da.full_name}
                for da in sorted({v.da.id: v.da for v in villages}.values(),
                                 key=lambda row: row.full_name.lower())],
        'villages': [{'id': v.id, 'name': v.name} for v in villages],
        'committees': sorted({c.committee_type for v in villages for c in v.committees
                              if c.is_enabled and not c.is_deleted and c.committee_type}),
    }
    if cluster:
        villages = [v for v in villages if v.da.pc.cluster.value == cluster]
    if da_id is not None:
        villages = [v for v in villages if v.da_id == da_id]
    if village_id is not None:
        villages = [v for v in villages if v.id == village_id]
    if committee_type:
        villages = [v for v in villages if any(c.committee_type == committee_type and
                     c.is_enabled and not c.is_deleted for c in v.committees)]

    authorized_ids = {v.id for v in villages}
    rows = list(db.session.scalars(
        scoped_select(VillageAttendanceVisit, user)
        .where(VillageAttendanceVisit.visit_date >= start,
               VillageAttendanceVisit.visit_date < cutoff,
               VillageAttendanceVisit.is_enabled.is_(True),
               VillageAttendanceVisit.is_deleted.is_(False))
        .options(selectinload(VillageAttendanceVisit.entries)
                 .selectinload(AttendanceEntry.committee))
    ).unique().all())
    rows = [v for v in rows if v.village_id in authorized_ids]
    current = [v for v in rows if chosen <= v.visit_date < cutoff]

    gender: Counter[str] = Counter({'Male': 0, 'Female': 0})
    committees: Counter[str] = Counter()
    performance: dict[int, dict[str, Any]] = {}
    cluster_visits: dict[str, set[int]] = defaultdict(set)
    active_visits = 0
    new_members = 0
    for visit in current:
        village = next((v for v in villages if v.id == visit.village_id), None)
        if village is None:
            continue
        active_visits += 1
        cluster_visits[village.da.pc.cluster.value].add(visit.village_id)
        new_members += (visit.new_members_count if visit.visit_month is not None
                        else sum(e.new_members_count for e in visit.entries if e.is_enabled and not e.is_deleted))
        person = performance.setdefault(visit.submitted_by_user_id,
                    {'user_id': visit.submitted_by_user_id, 'villages': set(), 'people': 0, 'visits': 0})
        person['villages'].add(visit.village_id)
        person['visits'] += 1
        for entry in visit.entries:
            if not entry.is_enabled or entry.is_deleted:
                continue
            if committee_type and entry.committee.committee_type != committee_type:
                continue
            count = entry.male_count + entry.female_count
            gender['Male'] += entry.male_count
            gender['Female'] += entry.female_count
            committees[entry.committee.committee_type or entry.committee.name] += count
            person['people'] += count

    # Only the already-scoped visit IDs and submitted user IDs are queried.
    names = {}
    for user_id in performance:
        actor = db.session.get(User, user_id)
        names[user_id] = actor.display_name if actor else 'User'
    performers = sorted(({'name': names[id_], 'villages': len(info['villages']),
                          'people': info['people'], 'visits': info['visits']}
                         for id_, info in performance.items()),
                        key=lambda item: (-item['villages'], -item['people'], item['name']))

    by_month: dict[date, dict[str, Any]] = {}
    for offset in range(6):
        key = _move_month(start, offset)
        by_month[key] = {'month': key.strftime('%b %Y'), 'visits': 0, 'people': 0, 'villages': set()}
    for visit in rows:
        key = visit.visit_date.replace(day=1)
        if key not in by_month:
            continue
        bucket = by_month[key]
        bucket['visits'] += 1
        bucket['villages'].add(visit.village_id)
        bucket['people'] += sum(e.male_count + e.female_count for e in visit.entries
                                if e.is_enabled and not e.is_deleted and
                                (not committee_type or e.committee.committee_type == committee_type))
    trend = [{'month': item['month'], 'visits': item['visits'], 'people': item['people'],
              'villages': len(item['villages'])} for item in by_month.values()]

    done_ids = {visit.village_id for visit in current}
    pending = [v for v in villages if v.id not in done_ids]
    cluster_denominators = Counter(v.da.pc.cluster.value for v in villages)
    cluster_data = [{'name': key, 'total': value, 'done': len(cluster_visits.get(key, set())),
                     'pending': value - len(cluster_visits.get(key, set()))}
                    for key, value in sorted(cluster_denominators.items())]
    return {
        'month': chosen.strftime('%Y-%m'), 'scope': 'actual-village-visits',
        'filters': filters,
        'counts': {'villages': len(villages), 'villages_done': len(done_ids),
                   'villages_pending': len(pending), 'visits': active_visits,
                   'people_attended': sum(gender.values()), 'new_members': new_members,
                   'committees_recorded': sum(1 for v in current for e in v.entries
                                              if e.is_enabled and not e.is_deleted and
                                              (not committee_type or e.committee.committee_type == committee_type))},
        'gender': dict(gender), 'committees': dict(committees),
        'clusters': cluster_data, 'das': performers, 'trend': trend,
        'pending': [{'id': v.id, 'name': v.name, 'cluster': v.da.pc.cluster.value}
                    for v in pending[:10]],
    }
