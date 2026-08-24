from __future__ import annotations

from datetime import timedelta

from itsdangerous import URLSafeTimedSerializer

from app.config import BaseConfig


def test_csrf_time_limit_is_integer_seconds():
    assert BaseConfig.WTF_CSRF_TIME_LIMIT == 43_200
    assert isinstance(BaseConfig.WTF_CSRF_TIME_LIMIT, int)
    assert not isinstance(BaseConfig.WTF_CSRF_TIME_LIMIT, timedelta)


def test_csrf_time_limit_is_accepted_by_itsdangerous():
    serializer = URLSafeTimedSerializer("test-secret", salt="wtf-csrf-token")
    token = serializer.dumps("session-token")

    assert (
        serializer.loads(token, max_age=BaseConfig.WTF_CSRF_TIME_LIMIT)
        == "session-token"
    )
