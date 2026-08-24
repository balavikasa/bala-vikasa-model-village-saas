
from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app(tmp_path: Path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "testing-secret-key-that-is-long-enough",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "SERVER_NAME": "localhost",
        }
    )
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
