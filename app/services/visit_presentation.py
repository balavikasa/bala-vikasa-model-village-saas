"""Presentation calculations over already permission-scoped records.

No database queries and no sample values live here. Callers must apply role
scoping before supplying records. Shared village visits are counted once.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def active_attendance(entry: Any) -> bool:
    if not entry.is_enabled or entry.is_deleted:
        return False
    parent = getattr(entry, "village_visit", None)
    return parent is None or (parent.is_enabled and not parent.is_deleted)


def visible_attendance(entries: list[Any], submitter_id: int | None = None) -> list[Any]:
    """Keep active evidence, and restrict Other-village evidence to its author."""
    return [entry for entry in entries if active_attendance(entry)
            and (submitter_id is None or entry.submitted_by_user_id == submitter_id)]


def _months_ending(today: date, count: int = 6) -> list[date]:
    index = today.year * 12 + today.month - 1
    return [date(n // 12, n % 12 + 1, 1) for n in range(index - count + 1, index + 1)]


def village_history(entries: list[Any], today: date) -> dict[str, Any]:
    groups: dict[Any, dict[str, Any]] = {}
    for entry in entries:
        if not active_attendance(entry) or entry.visit_date > today:
            continue
        visit_id = entry.village_visit_id
        key = ("visit", visit_id) if visit_id else ("legacy", entry.visit_date)
        row = groups.setdefault(key, {
            "date": entry.visit_date.isoformat(), "people": 0, "committees": 0,
            "report_url": (f"/reports/village/{visit_id}" if visit_id else
                           f"/reports/plan/{entry.action_plan_id}" if entry.action_plan_id else None),
        })
        row["people"] += entry.total_count
        row["committees"] += 1
    recent = sorted(groups.values(), key=lambda row: row["date"], reverse=True)
    trend = []
    for month in _months_ending(today):
        prefix = month.strftime("%Y-%m")
        rows = [row for row in recent if row["date"].startswith(prefix)]
        trend.append({"month": month.strftime("%b %Y"), "visits": len(rows),
                      "people": sum(row["people"] for row in rows)})
    return {"trend": trend, "recent_visits": recent[:6]}


def daily_visit_trend(visits: list[Any], today: date, days: int = 7) -> list[dict[str, Any]]:
    """Daily actual submissions, including zero days, no planned/future activity."""
    dates = [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]
    totals = {day: {"date": day.isoformat(), "label": day.strftime("%d %b"),
                    "visits": 0, "people": 0} for day in dates}
    for visit in visits:
        if visit.visit_date not in totals or not visit.is_enabled or visit.is_deleted:
            continue
        row = totals[visit.visit_date]
        row["visits"] += 1
        row["people"] += sum(entry.total_count for entry in visit.entries
                             if entry.is_enabled and not entry.is_deleted)
    return list(totals.values())
