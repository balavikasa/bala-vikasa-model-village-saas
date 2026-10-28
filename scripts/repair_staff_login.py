#!/usr/bin/env python3
"""Inspect or interactively repair a linked DA/PC login in Model Village SaaS.

Runs in the application's existing environment. Dry-run by default.
Requires an explicitly configured PostgreSQL DATABASE_URL and a server shell.
No password is accepted through CLI arguments or printed in logs.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Works when invoked from repository root as `python scripts/repair_staff_login.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from email_validator import EmailNotValidError, validate_email  # noqa: E402
from sqlalchemy import func  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app import APP_RELEASE, create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import DA, PC, AuditAction, Role, User  # noqa: E402
from app.services.audit import record_audit  # noqa: E402


def args_from_cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect or repair an existing DA/PC User account; no account is created."
    )
    parser.add_argument("--role", choices=("da", "pc"), required=True)
    parser.add_argument("--staff-id", type=int, required=True)
    parser.add_argument("--login-email", help="Desired login email; unchanged if omitted")
    parser.add_argument("--login-mobile", help="Desired 10-digit mobile; unchanged if omitted")
    parser.add_argument("--enable", action="store_true", help="Explicitly enable the User account")
    parser.add_argument("--apply", action="store_true", help="Change account after interactive confirmation")
    return parser.parse_args()


def format_time(value: datetime | None) -> str:
    if value is None:
        return "none"
    return value.replace(tzinfo=value.tzinfo or UTC).astimezone(UTC).isoformat()


def normalized_mobile(value: str | None) -> str | None:
    if not value:
        return None
    stripped = value.strip().replace("+", "").replace(" ", "").replace("-", "")
    stripped = stripped.replace("(", "").replace(")", "")
    if not stripped.isdigit() or not (
        len(stripped) == 10 or (len(stripped) == 11 and stripped.startswith("0"))
        or (len(stripped) == 12 and stripped.startswith("91"))
    ):
        raise ValueError("Mobile must be a 10-digit Indian number (optionally +91 or leading 0).")
    return stripped[-10:]


def resolve_login_email(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized.casefold()
    except EmailNotValidError as exc:
        raise ValueError("Invalid login email address.") from exc


def run() -> int:
    args = args_from_cli()
    raw_url = os.getenv("DATABASE_URL", "")
    if not raw_url.startswith(("postgresql://", "postgresql+psycopg://", "postgres://")):
        print("STOP: DATABASE_URL must explicitly point to PostgreSQL.", file=sys.stderr)
        return 2
    app = create_app("production")
    with app.app_context():
        model, role, profile_column = (
            (DA, Role.DA, User.da_id) if args.role == "da" else (PC, Role.PC, User.pc_id)
        )
        staff = db.session.get(model, args.staff_id)
        if staff is None or staff.is_deleted:
            print("STOP: Staff profile not found or deleted.", file=sys.stderr)
            return 2
        user = db.session.scalar(
            db.select(User).where(
                profile_column == staff.id,
                User.role == role,
                User.is_deleted.is_(False),
            )
        )
        if user is None:
            print("STOP: No existing active DA/PC User is linked to this staff profile.", file=sys.stderr)
            print("Use the Admin Users workflow to create or restore the linked account.")
            return 2

        print(f"Release: {APP_RELEASE}; database dialect: {db.engine.dialect.name}")
        print(f"Staff profile: {args.role.upper()} #{staff.id} - {staff.full_name}")
        print(f"Linked User #{user.id}: {user.display_name}; role: {user.role.value}")
        print(f"LOGIN email: {user.email or '(none)'}")
        print(f"LOGIN mobile: {user.mobile or '(none)'}")
        print(f"Profile email: {getattr(staff, 'email', None) or '(none)'}")
        print(f"Profile mobile: {getattr(staff, 'mobile', None) or '(none)'}")
        print(f"Enabled: {user.is_enabled}; deleted: {user.is_deleted}")
        print(f"Failed attempts: {user.failed_login_count}; lock expiry UTC: {format_time(user.locked_until)}")
        print(f"Password last changed UTC: {format_time(user.password_changed_at)}")
        if user.email != getattr(staff, "email", None) or user.mobile != getattr(staff, "mobile", None):
            print("NOTE: Staff contact and User login identifiers differ.")

        try:
            email = resolve_login_email(args.login_email) if args.login_email is not None else user.email
            mobile = normalized_mobile(args.login_mobile) if args.login_mobile is not None else user.mobile
        except ValueError as exc:
            print(f"STOP: {exc}", file=sys.stderr)
            return 2
        if not email and not mobile:
            print("STOP: A login email or mobile is required.", file=sys.stderr)
            return 2
        if email is not None:
            duplicate_email = db.session.scalar(
                db.select(User.id).where(User.id != user.id, func.lower(User.email) == email.casefold())
            )
            if duplicate_email is not None:
                print("STOP: Login email is owned by another User. Nothing changed.", file=sys.stderr)
                return 2
        if mobile is not None:
            other_users = db.session.scalars(db.select(User).where(User.id != user.id)).all()
            if any(
                ("".join(ch for ch in (other.mobile or "") if ch.isdigit()))[-10:] == mobile
                for other in other_users if other.mobile
            ):
                print("STOP: Mobile is owned by another User. Nothing changed.", file=sys.stderr)
                return 2
        print(f"Proposed login email: {email or '(none)'}; mobile: {mobile or '(none)'}")
        print(f"Proposed enabled: {user.is_enabled or args.enable}")
        if not args.apply:
            print("DRY RUN ONLY: no database changes. Pass --apply to reset interactively.")
            return 0
        if not sys.stdin.isatty():
            print("STOP: Interactive terminal required. Do not pass a password on the command line.", file=sys.stderr)
            return 2
        token = f"RESET {args.role.upper()} {staff.id}"
        if input(f"Type {token} to confirm this account: ").strip() != token:
            print("Cancelled; no changes.")
            return 1
        password = getpass.getpass("New password (not echoed): ")
        confirmation = getpass.getpass("Confirm password (not echoed): ")
        if not 6 <= len(password) <= 128 or password != confirmation:
            print("STOP: Password must be 6-128 characters and match confirmation.", file=sys.stderr)
            return 2
        if user.check_password(password):
            print("STOP: New password must differ from the existing one.", file=sys.stderr)
            return 2
        before = {
            "email": user.email, "mobile": user.mobile, "is_enabled": user.is_enabled,
            "password_changed_at": format_time(user.password_changed_at),
        }
        user.email = email
        user.mobile = mobile
        if args.enable:
            user.is_enabled = True
        user.failed_login_count = 0
        user.locked_until = None
        user.set_password(password)
        record_audit(AuditAction.UPDATE, user, before=before, after={
            "email": user.email, "mobile": user.mobile, "is_enabled": user.is_enabled,
            "password_changed_at": format_time(user.password_changed_at),
            "password_reset": True, "source": "staff-login-repair-cli",
        })
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            print("STOP: Database uniqueness conflict. No change committed.", file=sys.stderr)
            return 2
        finally:
            # Remove references to plaintext in the script's scope as soon as practical.
            password = None
            confirmation = None
        print("SUCCESS: linked User credentials updated; lockout cleared; audit recorded.")
        print(f"Sign in with: {user.email or user.mobile}")
        if not user.is_active:
            print("WARNING: User is still disabled; pass --enable after checking authorization.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
