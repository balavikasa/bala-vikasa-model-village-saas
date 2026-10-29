from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('coverage_exports', ROOT / 'app/reporting_exports.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

class ExportTests(unittest.TestCase):

    def data(self):
        return {'period': {'label': 'October 2026', 'timezone': 'Asia/Kolkata'}, 'filters_applied': {'status': 'pending', 'q': '=evil'}, 'counts': {'villages': 43, 'villages_done': 2, 'villages_pending': 41}, 'selection_counts': {'villages': 1, 'people_attended': 0, 'new_members': 0}, 'all_items': [{'id': 3, 'name': '=HYPERLINK("bad")', 'status': 'Pending', 'male': None, 'female': None, 'people_attended': None, 'new_members': None}], 'submissions': [], 'team': [], 'monthly_coverage': [], 'definitions': {'people': 'Attendance instances'}}

    def test_export_does_not_use_only_visible_page(self):
        d = self.data()
        d['items'] = []
        w = module.coverage_workbook(d)
        self.assertEqual(w['Villages'].max_row, 2)
        self.assertEqual(w['Villages'].cell(2, 2).value, '\'=HYPERLINK("bad")')
        self.assertIn('Pending', w.sheetnames)
        self.assertNotIn('Done', w.sheetnames)

    def test_csv_formula_and_blank_pending_counts(self):
        text = module.coverage_csv(self.data())
        self.assertIn("'=HYPERLINK", text)
        self.assertNotIn('None', text)

    def test_export_includes_selection_summary(self):
        w = module.coverage_workbook(self.data())
        rows = list(w['Summary'].values)
        self.assertIn(('Selection: people_attended', 0), rows)
if __name__ == '__main__':
    unittest.main()
