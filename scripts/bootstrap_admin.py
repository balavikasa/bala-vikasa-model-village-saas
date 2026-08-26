#!/usr/bin/env python3
"""Create or rotate the first administrator without exposing a password on the command line."""
from __future__ import annotations

import datetime as dt
import getpass
import os
import sys

from sqlalchemy import Boolean, Date, DateTime, String

from app import create_app
from app.extensions import db
from app.models import Role, User


def _required_value(column, email: str):
    env_name = f"BOOTSTRAP_ADMIN_{column.name.upper()}"
    supplied = os.getenv(env_name)
    if supplied not in (None, ""):
        return supplied
    name = column.name.lower()
    if "name" in name:
        return "System Administrator"
    if "email" in name or "login" in name or "identifier" in name:
        return email
    if isinstance(column.type, Boolean):
        return name == "is_enabled"
    if isinstance(column.type, DateTime):
        return dt.datetime.now(dt.UTC)
    if isinstance(column.type, Date):
        return dt.date.today()
    if isinstance(column.type, String):
        value = input(f"{column.name}: ").strip()
        if value:
            return value
    raise RuntimeError(
        f"Required User column {column.name!r} has no safe bootstrap default; "
        f"set {env_name}."
    )


def main() -> int:
    app = create_app()
    with app.app_context():
        email = (os.getenv("BOOTSTRAP_ADMIN_EMAIL") or input("Admin email: ")).strip().lower()
        mobile = (os.getenv("BOOTSTRAP_ADMIN_MOBILE") or "").strip() or None
        password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
        if len(password) < 6:
            print("Password must contain at least 6 characters.", file=sys.stderr)
            return 2

        user = User.query.filter_by(email=email).one_or_none()
        created = user is None
        if user is None:
            user = User()
            db.session.add(user)

        if hasattr(user, "email"):
            user.email = email
        if hasattr(user, "mobile") and mobile:
            user.mobile = mobile
        user.role = Role.ADMIN
        if hasattr(user, "is_enabled"):
            user.is_enabled = True
        if hasattr(user, "is_deleted"):
            user.is_deleted = False
        if hasattr(user, "deleted_at"):
            user.deleted_at = None

        # Fill any project-specific non-null column without hiding it in the script.
        for column in User.__table__.columns:
            if column.primary_key or column.nullable:
                continue
            if column.default is not None or column.server_default is not None:
                continue
            if column.name in {"email", "password_hash", "role"}:
                continue
            if getattr(user, column.name, None) is None:
                setattr(user, column.name, _required_value(column, email))

        if hasattr(user, "set_password"):
            user.set_password(password)
        else:
            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash(password)

        db.session.commit()
        print(f"{'Created' if created else 'Updated'} administrator {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
