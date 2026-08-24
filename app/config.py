from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'model_village.db'}")
    # Coolify commonly exposes PostgreSQL URLs as postgres://...
    # Use the explicit SQLAlchemy Psycopg 3 dialect installed by this release.
    if value.startswith("postgres://"):
        value = "postgresql+psycopg://" + value.removeprefix("postgres://")
    elif value.startswith("postgresql://"):
        value = "postgresql+psycopg://" + value.removeprefix("postgresql://")
    return value


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    SESSION_PROTECTION = os.getenv("SESSION_PROTECTION", "basic").strip().lower() or "basic"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.getenv("SESSION_HOURS", "12")))

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "8")) * 1024 * 1024
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "instance" / "uploads"))
    PHOTO_MAX_EDGE = int(os.getenv("PHOTO_MAX_EDGE", "1920"))
    PHOTO_WEBP_QUALITY = int(os.getenv("PHOTO_WEBP_QUALITY", "82"))

    RECYCLE_RETENTION_DAYS = int(os.getenv("RECYCLE_RETENTION_DAYS", "10"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    TRUST_PROXY = os.getenv("TRUST_PROXY", "0") == "1"
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Kolkata")

    # Flask-WTF / ItsDangerous expect max_age as integer seconds, not timedelta.
    WTF_CSRF_TIME_LIMIT = int(os.getenv("WTF_CSRF_TIME_LIMIT_SECONDS", "43200"))
    WTF_CSRF_HEADERS = ["X-CSRFToken", "X-CSRF-Token"]
    DASH_URL_BASE_PATHNAME = "/dash/"


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


class TestingConfig(BaseConfig):
    TESTING = True
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = str(BASE_DIR / "instance" / "test-uploads")


CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
