from __future__ import annotations

from datetime import date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app


DEFAULT_TIMEZONE = "Asia/Kolkata"
IST_FALLBACK = timezone(timedelta(hours=5, minutes=30), name="IST")


def app_zone() -> tzinfo:
    """Return the configured application timezone.

    Windows Python installations may not ship the IANA timezone database.
    ``tzdata`` is therefore an application dependency, but the India program
    still has a safe fixed-offset fallback so login/rendering cannot fail only
    because the host timezone database is unavailable.
    """

    name = current_app.config.get("APP_TIMEZONE", DEFAULT_TIMEZONE)
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        if name != DEFAULT_TIMEZONE:
            try:
                return ZoneInfo(DEFAULT_TIMEZONE)
            except ZoneInfoNotFoundError:
                pass
        return IST_FALLBACK


def local_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(app_zone())


def local_today() -> date:
    return local_now().date()


def current_month() -> date:
    return local_today().replace(day=1)
