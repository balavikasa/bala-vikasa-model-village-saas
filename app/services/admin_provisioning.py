"""Validate optional linked staff-login credentials before writing Admin records.

Pure validation so the same rules can be tested without a live Flask database.
This module never logs or serializes passwords.
"""
from __future__ import annotations

from email_validator import EmailNotValidError, validate_email


def normalize_staff_login(data: dict) -> dict[str, str | None]:
    """Return validated, normalized login fields for explicit staff provisioning."""
    if data.get("create_login") is not True:
        raise ValueError("create_login must be true to provision a staff account.")
    email = data.get("login_email")
    mobile = data.get("login_mobile")
    password = data.get("login_password")
    if email is not None and not isinstance(email, str):
        raise ValueError("Login email must be text.")
    if mobile is not None and not isinstance(mobile, str):
        raise ValueError("Login mobile must be text.")
    email = email.strip().casefold() if email else None
    if email:
        try:
            email = validate_email(email, check_deliverability=False).normalized
        except EmailNotValidError as exc:
            raise ValueError("Enter a valid login email address.") from exc
        if len(email) > 254:
            raise ValueError("Login email is too long.")
    if mobile:
        digits = "".join(char for char in mobile if char.isdigit())
        stripped = mobile.translate(str.maketrans("", "", "+- ()"))
        if not stripped.isdigit() or not (
            len(digits) == 10 or len(digits) == 11 and digits.startswith("0")
            or len(digits) == 12 and digits.startswith("91")
        ):
            raise ValueError("Enter a valid 10-digit Indian login mobile number.")
        mobile = digits[-10:]
    else:
        mobile = None
    if not email and not mobile:
        raise ValueError("Provide at least one login email or mobile number.")
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise ValueError("Login password must be 12–128 characters long.")
    return {"email": email, "mobile": mobile, "password": password}
