from __future__ import annotations

import enum
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from flask import has_request_context, request
from flask_login import current_user
from sqlalchemy import inspect

from ..extensions import db
from ..models import AuditAction, AuditLog, RecycleBin, User, utcnow

SENSITIVE_FIELDS = {"password_hash"}


def json_value(value: Any) -> Any:
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    return value


def model_snapshot(record: Any) -> dict[str, Any]:
    mapper = inspect(record).mapper
    result: dict[str, Any] = {}
    for column in mapper.columns:
        key = column.key
        if key in SENSITIVE_FIELDS:
            continue
        result[key] = json_value(getattr(record, key))
    return result


def display_name(record: Any) -> str:
    for attr in ("display_name", "full_name", "name", "title", "email", "mobile"):
        value = getattr(record, attr, None)
        if value:
            return str(value)
    return f"{type(record).__name__} #{getattr(record, 'id', '?')}"


def _request_metadata() -> dict[str, Any]:
    if not has_request_context():
        return {}
    forwarded = request.headers.get("X-Forwarded-For", "")
    ip = forwarded.split(",", 1)[0].strip() or request.remote_addr
    return {
        "request_id": request.headers.get("X-Request-ID"),
        "ip_address": ip,
        "user_agent": request.user_agent.string[:300] if request.user_agent else None,
    }


def record_audit(
    action: AuditAction | str,
    record: Any,
    *,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    actor: User | None = None,
) -> AuditLog:
    resolved_action = action if isinstance(action, AuditAction) else AuditAction(action)
    resolved_actor = actor
    if resolved_actor is None and has_request_context() and getattr(current_user, "is_authenticated", False):
        resolved_actor = current_user._get_current_object()

    row = AuditLog(
        actor_user_id=resolved_actor.id if resolved_actor else None,
        action=resolved_action,
        entity_type=type(record).__name__,
        entity_id=getattr(record, "id", None),
        before_json=before,
        after_json=after,
        **_request_metadata(),
    )
    db.session.add(row)
    return row


def soft_delete(record: Any, actor: User, retention_days: int = 10) -> RecycleBin:
    if not hasattr(record, "is_deleted"):
        raise ValueError(f"{type(record).__name__} does not support soft deletion.")
    if record.is_deleted:
        existing = db.session.scalar(
            db.select(RecycleBin)
            .where(
                RecycleBin.entity_type == type(record).__name__,
                RecycleBin.entity_id == record.id,
                RecycleBin.restored_at.is_(None),
            )
            .order_by(RecycleBin.deleted_at.desc())
        )
        if existing:
            return existing
        raise ValueError("Record is already deleted.")

    before = model_snapshot(record)
    now = utcnow()
    record.is_deleted = True
    record.is_enabled = False
    record.deleted_at = now
    bin_row = RecycleBin(
        entity_type=type(record).__name__,
        entity_id=record.id,
        display_name=display_name(record),
        snapshot_json=before,
        deleted_by_user_id=actor.id,
        deleted_at=now,
        purge_after=now + timedelta(days=retention_days),
    )
    db.session.add(bin_row)
    record_audit(AuditAction.DELETE, record, before=before, after=model_snapshot(record), actor=actor)
    return bin_row


def restore(record: Any, bin_row: RecycleBin, actor: User) -> None:
    if bin_row.restored_at is not None:
        raise ValueError("This recycle-bin item has already been restored.")
    if not getattr(record, "is_deleted", False):
        raise ValueError("The underlying record is not deleted.")

    before = model_snapshot(record)
    snapshot = bin_row.snapshot_json or {}
    record.is_deleted = False
    record.deleted_at = None
    record.is_enabled = bool(snapshot.get("is_enabled", True))
    bin_row.restored_at = utcnow()
    bin_row.restored_by_user_id = actor.id
    record_audit(AuditAction.RESTORE, record, before=before, after=model_snapshot(record), actor=actor)
