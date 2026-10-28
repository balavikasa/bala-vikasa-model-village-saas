import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ReferenceContract(unittest.TestCase):
    def test_reference_system_is_the_last_shared_style(self):
        base = (ROOT / 'app/templates/base.html').read_text()
        self.assertIn('css/reference-ui.css', base)
        self.assertIn('ref-topbar', base)
        self.assertIn('components/brand.html', base)
        brand = (ROOT / 'app/templates/components/brand.html').read_text()
        self.assertIn('brand/bala-vikasa-symbol.png', brand)
        self.assertNotIn('2026', brand)

    def test_six_pages_have_reference_compositions(self):
        for name in ['admin', 'overview', 'analytics', 'profile', 'village_attendance_report', 'village_attendance']:
            with self.subTest(name=name):
                self.assertIn('ref-', (ROOT / f'app/templates/{name}.html').read_text())

    def test_entry_preserves_business_hooks(self):
        text = (ROOT / 'app/templates/village_attendance.html').read_text()
        for id_ in ['village-select', 'visit-date', 'other-village-toggle', 'committee-attendance-cards', 'village-new-members', 'submit-village-attendance']:
            self.assertIn(f'id="{id_}"', text)
        self.assertIn('readonly', text)
        self.assertNotIn('counts per committee', text)

if __name__ == '__main__':
    unittest.main()
