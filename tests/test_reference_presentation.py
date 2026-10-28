"""Standalone tests for presentation calculations; no Flask/database dependency."""
import importlib.util
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace as NS


def helper():
    path = Path(__file__).resolve().parents[1] / 'app/services/visit_presentation.py'
    spec = importlib.util.spec_from_file_location('visit_presentation', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def entry(id, visit_id, day, total=5, enabled=True, parent_enabled=True):
    return NS(id=id, village_visit_id=visit_id, visit_date=day, total_count=total,
              is_enabled=enabled, is_deleted=False, action_plan_id=10,
              village_visit=NS(is_enabled=parent_enabled, is_deleted=False) if visit_id else None)


class Presentations(unittest.TestCase):
    def test_village_history_counts_shared_visit_once_and_attendance_per_committee(self):
        rows = [entry(1, 7, date(2026, 10, 28), 4), entry(2, 7, date(2026, 10, 28), 6),
                entry(3, 8, date(2026, 9, 28), 8)]
        result = helper().village_history(rows, date(2026, 10, 28))
        self.assertEqual(result['trend'][-1]['visits'], 1)
        self.assertEqual(result['trend'][-1]['people'], 10)
        self.assertEqual(len(result['recent_visits']), 2)
        self.assertEqual(result['recent_visits'][0]['report_url'], '/reports/village/7')
        self.assertEqual(result['recent_visits'][0]['committees'], 2)

    def test_disabled_visit_is_not_reported_through_enabled_child_rows(self):
        rows = [entry(1, 7, date(2026, 10, 28), parent_enabled=False),
                entry(2, 8, date(2026, 10, 28), enabled=False)]
        self.assertEqual(helper().village_history(rows, date(2026, 10, 28))['recent_visits'], [])

    def test_six_month_window_handles_year_boundary_and_no_future_entries(self):
        rows = [entry(1, 7, date(2026, 12, 28), 4), entry(2, 8, date(2027, 3, 1), 9)]
        result = helper().village_history(rows, date(2027, 1, 12))
        self.assertEqual(len(result['trend']), 6)
        self.assertEqual(result['trend'][0]['month'], 'Aug 2026')
        self.assertEqual(result['trend'][-1]['month'], 'Jan 2027')
        self.assertEqual(sum(r['people'] for r in result['trend']), 4)
        self.assertEqual(len(result['recent_visits']), 1)

    def test_other_village_evidence_excludes_other_submitters_and_disabled_parents(self):
        mine = entry(1, 7, date(2026, 10, 28))
        mine.submitted_by_user_id = 6
        someone_else = entry(2, 8, date(2026, 10, 28))
        someone_else.submitted_by_user_id = 9
        archived = entry(3, 9, date(2026, 10, 28), parent_enabled=False)
        archived.submitted_by_user_id = 6
        rows = [mine, someone_else, archived]
        self.assertEqual(helper().visible_attendance(rows, submitter_id=6), [mine])
        self.assertEqual(helper().visible_attendance(rows), [mine, someone_else])

    def test_daily_visit_series_keeps_zero_days_and_scoped_totals(self):
        visits = [NS(visit_date=date(2026,10,28), is_enabled=True, is_deleted=False,
                     entries=[entry(1, 7, date(2026,10,28), 3), entry(2, 7, date(2026,10,28), 4)])]
        rows = helper().daily_visit_trend(visits, date(2026,10,28), days=7)
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[-1]['visits'], 1)
        self.assertEqual(rows[-1]['people'], 7)
        self.assertEqual(rows[0]['visits'], 0)

if __name__ == '__main__':
    unittest.main()
