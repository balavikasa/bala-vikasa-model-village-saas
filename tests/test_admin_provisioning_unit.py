"""Dependency-light contract for optional Admin-created staff login credentials."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

HELPER = Path(__file__).resolve().parents[1] / 'app/services/admin_provisioning.py'


def module():
    spec = importlib.util.spec_from_file_location('admin_provisioning_isolated', HELPER)
    instance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instance)
    return instance


class AdminProvisioningTests(unittest.TestCase):
    def test_staff_signin_contact_can_be_distinct_from_profile_contact(self):
        normalize = module().normalize_staff_login
        result = normalize({
            'create_login': True, 'login_email': '  DA.New@Example.ORG ',
            'login_mobile': ' +91 98765 43210 ', 'login_password': 'DedicatedPassword123'
        })
        self.assertEqual(result['email'], 'da.new@example.org')
        self.assertEqual(result['mobile'], '9876543210')
        self.assertEqual(result['password'], 'DedicatedPassword123')

    def test_missing_login_identifier_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'email or mobile'):
            module().normalize_staff_login({'create_login': True,'login_password': 'DedicatedPassword123'})

    def test_short_password_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '12'):
            module().normalize_staff_login({'create_login': True,'login_email': 'person@example.org','login_password': 'short'})

    def test_duplicate_identity_input_format_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'mobile'):
            module().normalize_staff_login({'create_login': True,'login_email': 'person@example.org','login_mobile':'abc-not-phone','login_password':'DedicatedPassword123'})

    def test_nonboolean_provision_flag_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'create_login'):
            module().normalize_staff_login({'create_login': 'true','login_email':'person@example.org','login_password':'DedicatedPassword123'})


if __name__ == '__main__':
    unittest.main()
