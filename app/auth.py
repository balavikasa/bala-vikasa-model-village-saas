from __future__ import annotations

from datetime import UTC, timedelta
from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, or_

from .extensions import db
from .models import AuditAction, User, utcnow
from .services.audit import record_audit

bp = Blueprint("auth", __name__)


def _safe_next(target: str | None) -> bool:
    if not target:
        return False
    parts = urlsplit(target)
    return not parts.scheme and not parts.netloc and target.startswith("/")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pages.home"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        normalized_email = identifier.casefold()
        # Compare numeric digits without punctuation. Indian +91/0-prefixed
        # phone entries are accepted while never bypassing password checks.
        phone_characters = identifier.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        digits = "".join(ch for ch in identifier if ch.isdigit()) if phone_characters.isdigit() else ""
        mobile_variants = {identifier.strip(), digits, f"+{digits}"} if digits else set()
        if len(digits) == 12 and digits.startswith("91"):
            mobile_variants.update({digits[2:], f"0{digits[2:]}"})
        if len(digits) == 11 and digits.startswith("0"):
            mobile_variants.add(digits[1:])
        if len(digits) == 10:
            mobile_variants.update({f"91{digits}", f"+91{digits}", f"0{digits}"})
        user = db.session.scalar(
            db.select(User).where(
                or_(
                    func.lower(User.email) == normalized_email,
                    User.mobile.in_(mobile_variants) if mobile_variants else User.mobile.is_(None) & (User.id == -1),
                )
            )
        )
        now = utcnow()
        locked_until = user.locked_until if user else None
        # SQLite returns naive values for DateTime(timezone=True); PostgreSQL
        # normally returns aware ones. Both must be comparable to UTC now.
        if locked_until and locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=UTC)
        if user and locked_until and locked_until > now:
            flash("This account is temporarily locked. Contact an administrator or try later.", "error")
        elif user and user.is_active and user.check_password(password):
            user.failed_login_count = 0
            user.locked_until = None
            user.last_login_at = now
            record_audit(AuditAction.LOGIN, user, actor=user)
            db.session.commit()
            login_user(user, remember=True, fresh=True)
            next_url = request.args.get("next") or request.form.get("next")
            return redirect(next_url if _safe_next(next_url) else url_for("pages.home"))
        else:
            if user:
                user.failed_login_count += 1
                if user.failed_login_count >= 5:
                    user.locked_until = now + timedelta(minutes=15)
                db.session.commit()
            flash("Email/mobile or password is incorrect.", "error")

    return render_template("login.html", next_url=request.args.get("next", ""))


@bp.post("/logout")
@login_required
def logout():
    user = current_user._get_current_object()
    record_audit(AuditAction.LOGOUT, user, actor=user)
    db.session.commit()
    logout_user()
    return redirect(url_for("auth.login"))
