"""Real reporting calculations; executable without Flask for offline verification."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bv_reporting_core', ROOT / 'app/reporting_core.py')
core = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = core
spec.loader.exec_module(core)
TODAY = date(2026, 10, 29)

def village(id_, **kw):
    return dict(id=id_, name=f'Village {id_:03}', cluster='CSRB', pc_id=1, pc='PC One', assigned_da_id=1, assigned_da='DA One', in_scope=True, is_enabled=True, is_deleted=False, committee_types=['Water'], **kw)

def visit(id_, village_id, when='2026-10-28', male=11, female=13, new=29, **kw):
    return dict(id=id_, village_id=village_id, date=when, submitted_da_id=1, submitted_by='DA One', is_enabled=True, is_deleted=False, new_members=new, entries=[dict(male=male, female=female, committee='Water', committee_type='Water', is_enabled=True, is_deleted=False)], **kw)

class PeriodTests(unittest.TestCase):

    def test_calendar_boundaries(self):
        cases = [({'period': 'today'}, '2026-10-29', '2026-10-29'), ({'period': 'yesterday'}, '2026-10-28', '2026-10-28'), ({'period': 'this_week'}, '2026-10-26', '2026-11-01'), ({'period': 'last_week'}, '2026-10-19', '2026-10-25'), ({'period': 'last_month'}, '2026-09-01', '2026-09-30'), ({'month': '2024-02'}, '2024-02-01', '2024-02-29'), ({'period': 'custom', 'from': '2026-09-28', 'to': '2026-10-03'}, '2026-09-28', '2026-10-03')]
        for args, start, end in cases:
            with self.subTest(args=args):
                p = core.resolve_period(args, TODAY)
                self.assertEqual(p.start.isoformat(), start)
                self.assertEqual(p.end.isoformat(), end)
        p = core.resolve_period({'period': 'last_month'}, date(2026, 1, 1))
        self.assertEqual(p.start, date(2025, 12, 1))
        p = core.resolve_period({'period': 'last_week'}, date(2026, 1, 1))
        self.assertEqual((p.start, p.end), (date(2025, 12, 22), date(2025, 12, 28)))

    def test_invalid_and_reversed_dates(self):
        for args in ({'period': 'bad'}, {'period': 'custom', 'from': '2026-11-01', 'to': '2026-10-01'}, {'period': 'custom', 'from': '2026-02-30', 'to': '2026-03-01'}, {'month': 'oops'}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                core.resolve_period(args, TODAY)

    def test_all_time(self):
        p = core.resolve_period({'period': 'all'}, TODAY)
        self.assertIsNone(p.start)
        self.assertEqual(p.end, TODAY)

    def test_filters_fail_closed(self):
        for args in ({'da': '-1'}, {'pc': 'abc'}, {'page': '0'}, {'page_size': '10000'}, {'status': 'missing'}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                core.parse_filters(args)

class CoverageTests(unittest.TestCase):

    def report(self, villages=None, visits=None, args=None, team=None):
        return core.build_coverage(villages or [village(i) for i in range(1, 44)], visits or [], team or [], core.resolve_period(args or {}, TODAY), core.parse_filters(args or {}), TODAY)

    def test_43_villages_two_done_all_pending_reachable(self):
        data = self.report(visits=[visit(1, 1), visit(2, 2)], args={'status': 'pending', 'page_size': '25'})
        self.assertEqual((data['counts']['villages_done'], data['counts']['villages_pending']), (2, 41))
        self.assertEqual(data['total'], 41)
        self.assertEqual(len(data['items']), 25)
        self.assertEqual(data['selection_counts']['people_attended'], 0)
        data2 = self.report(visits=[visit(1, 1), visit(2, 2)], args={'status': 'pending', 'page': '2', 'page_size': '25'})
        self.assertEqual(len(data2['items']), 16)
        self.assertEqual(len({v['id'] for v in data['items'] + data2['items']}), 41)

    def test_search_counts_and_export_population_are_identical(self):
        data = self.report(visits=[visit(1, 1), visit(2, 2, male=5, female=5, new=0)], args={'q': 'Village 001'})
        self.assertEqual(data['counts']['people_attended'], 24)
        self.assertEqual(data['selection_counts']['people_attended'], 24)
        self.assertEqual([r['id'] for r in data['all_items']], [1])
        self.assertEqual([r['id'] for r in data['submissions']], [1])

    def test_new_members_not_multiplied_or_added_to_attendance(self):
        v = visit(1, 1)
        v['entries'] *= 3
        data = self.report(visits=[v])
        self.assertEqual(data['counts']['people_attended'], 72)
        self.assertEqual(data['counts']['new_members'], 29)

    def test_daily_weekly_and_monthly_use_same_engine(self):
        rows = [visit(1, 1, '2026-10-29'), visit(2, 2, '2026-10-26'), visit(3, 3, '2026-10-01')]
        for period, want in [('today', 1), ('this_week', 2), ('this_month', 3)]:
            data = self.report(visits=rows, args={'period': period})
            self.assertEqual(data['counts']['villages_done'], want)
            self.assertEqual(data['counts']['people_attended'], 24 * want)

    def test_more_than_120_visits(self):
        vs = [village(i) for i in range(1, 152)]
        data = self.report(villages=vs, visits=[visit(i, i) for i in range(1, 151)], args={'status': 'pending'})
        self.assertEqual(data['counts']['villages_done'], 150)
        self.assertEqual([r['id'] for r in data['all_items']], [151])

    def test_disabled_deleted_and_childless_do_not_count(self):
        vs = [village(i) for i in range(1, 6)]
        vs[1]['is_enabled'] = False
        vs[2]['is_deleted'] = True
        rows = [visit(i, i) for i in range(1, 6)]
        rows[3]['is_deleted'] = True
        rows[4]['entries'][0]['is_enabled'] = False
        data = self.report(villages=vs, visits=rows)
        self.assertEqual(data['counts']['villages'], 3)
        self.assertEqual(data['counts']['villages_done'], 1)
        self.assertEqual(data['counts']['people_attended'], 24)

    def test_other_village_does_not_expand_assignment(self):
        vs = [village(1), village(2)]
        vs[1].update(in_scope=False, assigned_da_id=2, assigned_da='DA Two')
        data = self.report(villages=vs, visits=[visit(1, 2)], args={'status': 'other'})
        self.assertEqual(data['counts']['villages'], 1)
        self.assertEqual(data['counts']['villages_pending'], 1)
        self.assertEqual(data['counts']['other_villages_visited'], 1)
        self.assertEqual(data['selection_counts']['people_attended'], 24)
        self.assertEqual(data['items'][0]['assigned_da'], 'DA Two')

    def test_assigned_da_and_actual_submitter_filters(self):
        vs = [village(1), village(2)]
        vs[1].update(assigned_da_id=2, assigned_da='DA Two')
        data = self.report(villages=vs, visits=[visit(1, 2)], args={'submitted_da': '1'})
        self.assertEqual(data['counts']['villages_done'], 1)
        data = self.report(villages=vs, visits=[visit(1, 2)], args={'da': '1'})
        self.assertEqual(data['counts']['villages_done'], 0)

    def test_zero_activity_da_and_cross_village_performance(self):
        vs = [village(1), village(2)]
        vs[1].update(assigned_da_id=2, assigned_da='DA Two')
        team = [dict(id=1, name='DA One', pc_id=1, pc='PC One', cluster='CSRB'), dict(id=2, name='DA Two', pc_id=1, pc='PC One', cluster='CSRB')]
        data = self.report(villages=vs, visits=[visit(1, 2)], team=team)
        people = {r['id']: r for r in data['team']}
        self.assertEqual(people[1]['done'], 0)
        self.assertEqual(people[1]['other_visits'], 1)
        self.assertEqual(people[1]['people_attended'], 24)
        self.assertEqual(people[2]['done'], 1)
        self.assertEqual(people[2]['visits'], 0)

    def test_multimonth_unique_coverage_is_not_monthly_completion(self):
        data = self.report(villages=[village(1)], visits=[visit(1, 1, '2026-09-01')], args={'period': 'custom', 'from': '2026-09-01', 'to': '2026-10-29'})
        self.assertEqual(data['counts']['villages_done'], 1)
        months = {r['month']: r for r in data['monthly_coverage']}
        self.assertEqual(months['2026-09']['done'], 1)
        self.assertEqual(months['2026-10']['pending'], 1)

    def test_pending_rows_have_no_fabricated_attendance(self):
        data = self.report(villages=[village(1)], visits=[visit(1, 1, '2026-09-15')])
        row = data['items'][0]
        self.assertIsNone(row['male'])
        self.assertIsNone(row['people_attended'])
        self.assertEqual(row['last_visit'], '2026-09-15')
        self.assertIsNone(row['report_url'])

    def test_status_filters_do_not_corrupt_scope_counts(self):
        data = self.report(visits=[visit(1, 1)], args={'status': 'pending', 'q': 'Village 00'})
        self.assertEqual(data['counts']['villages'], 9)
        self.assertEqual(data['counts']['villages_done'] + data['counts']['villages_pending'], 9)
        self.assertEqual(data['selection_counts']['villages'], 8)

    def test_same_village_multiple_visits_counts_one_done(self):
        data = self.report(visits=[visit(1, 1), visit(2, 1, '2026-10-01')])
        self.assertEqual(data['counts']['villages_done'], 1)
        self.assertEqual(data['counts']['visits'], 2)

    def test_unselected_committee_does_not_create_done(self):
        vs = [village(1)]
        vs[0]['committee_types'] = ['Water', 'Health']
        data = self.report(villages=vs, visits=[visit(1, 1)], args={'committee': 'Health'})
        self.assertEqual(data['counts']['villages_done'], 0)

    def test_unknown_village_never_enters_totals(self):
        data = self.report(villages=[village(1)], visits=[visit(1, 999)])
        self.assertEqual(data['counts']['people_attended'], 0)
if __name__ == '__main__':
    unittest.main()
