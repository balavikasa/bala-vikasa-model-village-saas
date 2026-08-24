from __future__ import annotations


def test_session_protection_defaults_to_basic(app):
    assert app.login_manager.session_protection == "basic"
