from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import abort, jsonify
from flask_login import current_user
from sqlalchemy import Select, false, select

from .extensions import db
from .models import (
    DA,
    PC,
    ActionPlan,
    AttendanceEntry,
    AuditLog,
    Committee,
    CommitteeMember,
    RecycleBin,
    Role,
    SpecialsEntry,
    User,
    Village,
)

T = TypeVar("T")


class ScopeError(PermissionError):
    """Raised when a record is outside a user's visibility or write scope."""


GLOBAL_READ_ROLES = {Role.ADMIN, Role.PM}
WRITE_ROLES = {Role.ADMIN, Role.DA}
ADMIN_ONLY_MODELS = {AuditLog, RecycleBin}


def active_clause(model: type[Any]):
    clauses = []
    if hasattr(model, "is_deleted"):
        clauses.append(model.is_deleted.is_(False))
    if hasattr(model, "is_enabled"):
        clauses.append(model.is_enabled.is_(True))
    return clauses


def scoped_select(
    model: type[T],
    user: User,
    *,
    include_disabled: bool = False,
    include_deleted: bool = False,
) -> Select[tuple[T]]:
    """Return a SELECT constrained to the rows visible to ``user``.

    This is the single authorization boundary used by page/API read paths. Cluster is
    never read from DA or Village columns; it is derived through DA.pc.cluster.
    """

    stmt = select(model)
    if hasattr(model, "is_deleted") and not include_deleted:
        stmt = stmt.where(model.is_deleted.is_(False))
    # Admin is the recovery/maintenance role and must see disabled records so they
    # can be re-enabled. PM/PC/DA only see enabled data unless a privileged caller
    # explicitly opts into disabled rows.
    if (
        hasattr(model, "is_enabled")
        and not include_disabled
        and getattr(user, "role", None) != Role.ADMIN
    ):
        stmt = stmt.where(model.is_enabled.is_(True))

    if not user.is_authenticated or not user.is_active:
        return stmt.where(false())

    if user.role in GLOBAL_READ_ROLES:
        return stmt

    if model in ADMIN_ONLY_MODELS:
        return stmt.where(false())

    if user.role == Role.PC:
        if not user.pc_id:
            return stmt.where(false())
        pc_id = user.pc_id

        if model is PC:
            return stmt.where(PC.id == pc_id)
        if model is DA:
            return stmt.where(DA.pc_id == pc_id)
        if model is Village:
            return stmt.join(Village.da).where(DA.pc_id == pc_id)
        if model is Committee:
            return stmt.join(Committee.village).join(Village.da).where(DA.pc_id == pc_id)
        if model is CommitteeMember:
            return (
                stmt.join(CommitteeMember.committee)
                .join(Committee.village)
                .join(Village.da)
                .where(DA.pc_id == pc_id)
            )
        if model is ActionPlan:
            return (
                stmt.join(ActionPlan.committee)
                .join(Committee.village)
                .join(Village.da)
                .where(DA.pc_id == pc_id)
            )
        if model is AttendanceEntry:
            return stmt.join(AttendanceEntry.village).join(Village.da).where(DA.pc_id == pc_id)
        if model is SpecialsEntry:
            return stmt.join(SpecialsEntry.village).join(Village.da).where(DA.pc_id == pc_id)
        if model is User:
            return stmt.where((User.id == user.id) | (User.da_id.in_(select(DA.id).where(DA.pc_id == pc_id))))
        return stmt.where(false())

    if user.role == Role.DA:
        if not user.da_id:
            return stmt.where(false())
        da_id = user.da_id

        if model is DA:
            return stmt.where(DA.id == da_id)
        if model is PC:
            return stmt.join(PC.das).where(DA.id == da_id)
        if model is Village:
            return stmt.where(Village.da_id == da_id)
        if model is Committee:
            return stmt.join(Committee.village).where(Village.da_id == da_id)
        if model is CommitteeMember:
            return stmt.join(CommitteeMember.committee).join(Committee.village).where(Village.da_id == da_id)
        if model is ActionPlan:
            return stmt.join(ActionPlan.committee).join(Committee.village).where(Village.da_id == da_id)
        if model is AttendanceEntry:
            return stmt.join(AttendanceEntry.village).where(Village.da_id == da_id)
        if model is SpecialsEntry:
            return stmt.join(SpecialsEntry.village).where(Village.da_id == da_id)
        if model is User:
            return stmt.where(User.id == user.id)
        return stmt.where(false())

    return stmt.where(false())


def scoped_get(
    model: type[T],
    record_id: int,
    user: User,
    *,
    include_disabled: bool = False,
    include_deleted: bool = False,
) -> T | None:
    stmt = scoped_select(
        model,
        user,
        include_disabled=include_disabled,
        include_deleted=include_deleted,
    ).where(model.id == record_id)
    return db.session.scalar(stmt)


def require_scoped(
    model: type[T],
    record_id: int,
    user: User,
    *,
    include_disabled: bool = False,
    include_deleted: bool = False,
) -> T:
    record = scoped_get(
        model,
        record_id,
        user,
        include_disabled=include_disabled,
        include_deleted=include_deleted,
    )
    if record is None:
        raise ScopeError(f"{model.__name__} is not available in your assigned scope.")
    return record


def can_submit_for_village(user: User, village: Village) -> bool:
    if not user.is_authenticated or not user.is_active:
        return False
    return user.role == Role.DA and user.da_id == village.da_id


def can_manage_action_plan(user: User, committee: Committee) -> bool:
    if user.role == Role.ADMIN:
        return True
    return (
        user.role == Role.PC
        and user.pc_id is not None
        and committee.village.da.pc_id == user.pc_id
    )


def role_required(*roles: Role | str) -> Callable:
    allowed = {role if isinstance(role, Role) else Role(role) for role in roles}

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in allowed:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def json_role_required(*roles: Role | str) -> Callable:
    allowed = {role if isinstance(role, Role) else Role(role) for role in roles}

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any):
            if not current_user.is_authenticated:
                return jsonify(error="Authentication required."), 401
            if current_user.role not in allowed:
                return jsonify(error="You do not have permission for this operation."), 403
            return view(*args, **kwargs)

        return wrapped

    return decorator


def inherited_cluster(record: Any) -> str | None:
    if isinstance(record, PC):
        return record.cluster.value
    if isinstance(record, DA):
        return record.pc.cluster.value
    if isinstance(record, Village):
        return record.da.pc.cluster.value
    if isinstance(record, Committee):
        return record.village.da.pc.cluster.value
    if isinstance(record, CommitteeMember):
        return record.committee.village.da.pc.cluster.value
    if isinstance(record, ActionPlan):
        return record.committee.village.da.pc.cluster.value
    if isinstance(record, (AttendanceEntry, SpecialsEntry)):
        return record.village.da.pc.cluster.value
    return None


def visible_village_ids(user: User) -> list[int]:
    return list(db.session.scalars(scoped_select(Village, user).with_only_columns(Village.id)).all())
