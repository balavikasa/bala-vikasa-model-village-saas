from __future__ import annotations

from datetime import timedelta
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
        normalized_mobile = "".join(ch for ch in identifier if ch.isdigit() or ch == "+")
        user = db.session.scalar(
            db.select(User).where(
                or_(
                    func.lower(User.email) == normalized_email,
                    User.mobile == normalized_mobile,
                )
            )
        )
        now = utcnow()
        if user and user.locked_until and user.locked_until > now:
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
