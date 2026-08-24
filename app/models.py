from __future__ import annotations

import enum
from datetime import UTC, date, datetime
from typing import Any

from flask_login import UserMixin
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow() -> datetime:
    return datetime.now(UTC)


class Role(str, enum.Enum):
    ADMIN = "admin"
    PM = "pm"
    PC = "pc"
    DA = "da"


class Cluster(str, enum.Enum):
    CSRB = "CSRB"
    PDTC = "PDTC"


class AttendanceStatus(str, enum.Enum):
    EARLY = "Early"
    ON_TIME = "On-time"
    POSTPONED = "Postponed"


class ActionPlanType(str, enum.Enum):
    ATTENDANCE = "Attendance"
    SPECIALS = "Specials"


class SpecialScope(str, enum.Enum):
    GP = "Under GP"
    VDC = "Under VDC"


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    MOVE = "move"
    ENABLE = "enable"
    DISABLE = "disable"
    DELETE = "delete"
    RESTORE = "restore"
    PURGE = "purge"
    LOGIN = "login"
    LOGOUT = "logout"
    IMPORT = "import"


enum_options = {
    "native_enum": False,
    "validate_strings": True,
    "values_callable": lambda enum_cls: [member.value for member in enum_cls],
}


class LifecycleMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"), index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class PM(LifecycleMixin, db.Model):
    __tablename__ = "pms"

    full_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    mobile: Mapped[str | None] = mapped_column(String(24), unique=True)
    notes: Mapped[str | None] = mapped_column(Text)

    users: Mapped[list[User]] = relationship(back_populates="pm")

    def __repr__(self) -> str:
        return f"<PM {self.full_name!r}>"


class PC(LifecycleMixin, db.Model):
    __tablename__ = "pcs"

    full_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    cluster: Mapped[Cluster] = mapped_column(Enum(Cluster, **enum_options), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    mobile: Mapped[str | None] = mapped_column(String(24), unique=True)
    notes: Mapped[str | None] = mapped_column(Text)

    das: Mapped[list[DA]] = relationship(back_populates="pc")
    users: Mapped[list[User]] = relationship(back_populates="pc")

    def __repr__(self) -> str:
        return f"<PC {self.full_name!r} {self.cluster.value}>"


class DA(LifecycleMixin, db.Model):
    __tablename__ = "das"

    full_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    pc_id: Mapped[int] = mapped_column(ForeignKey("pcs.id", ondelete="RESTRICT"), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    mobile: Mapped[str | None] = mapped_column(String(24), unique=True)
    notes: Mapped[str | None] = mapped_column(Text)

    pc: Mapped[PC] = relationship(back_populates="das")
    villages: Mapped[list[Village]] = relationship(back_populates="da")
    users: Mapped[list[User]] = relationship(back_populates="da")

    @property
    def cluster(self) -> Cluster:
        return self.pc.cluster

    def __repr__(self) -> str:
        return f"<DA {self.full_name!r}>"


class Village(LifecycleMixin, db.Model):
    __tablename__ = "villages"
    __table_args__ = (
        UniqueConstraint("da_id", "name", name="uq_villages_da_name"),
        Index("ix_villages_coordinates", "latitude", "longitude"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(40), unique=True)
    gp_name: Mapped[str | None] = mapped_column(String(160))
    district: Mapped[str | None] = mapped_column(String(120))
    mandal: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    da_id: Mapped[int] = mapped_column(ForeignKey("das.id", ondelete="RESTRICT"), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    da: Mapped[DA] = relationship(back_populates="villages")
    committees: Mapped[list[Committee]] = relationship(back_populates="village")
    attendance_entries: Mapped[list[AttendanceEntry]] = relationship(back_populates="village")
    specials_entries: Mapped[list[SpecialsEntry]] = relationship(back_populates="village")

    @property
    def cluster(self) -> Cluster:
        return self.da.pc.cluster

    def __repr__(self) -> str:
        return f"<Village {self.name!r}>"


class Committee(LifecycleMixin, db.Model):
    __tablename__ = "committees"
    __table_args__ = (UniqueConstraint("village_id", "name", name="uq_committees_village_name"),)

    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    committee_type: Mapped[str | None] = mapped_column(String(100), index=True)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id", ondelete="RESTRICT"), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    village: Mapped[Village] = relationship(back_populates="committees")
    members: Mapped[list[CommitteeMember]] = relationship(back_populates="committee")
    action_plans: Mapped[list[ActionPlan]] = relationship(back_populates="committee")
    attendance_entries: Mapped[list[AttendanceEntry]] = relationship(back_populates="committee")
    specials_entries: Mapped[list[SpecialsEntry]] = relationship(back_populates="committee")

    @property
    def active_member_count(self) -> int:
        return sum(1 for member in self.members if member.is_enabled and not member.is_deleted)

    def __repr__(self) -> str:
        return f"<Committee {self.name!r}>"


class CommitteeMember(LifecycleMixin, db.Model):
    __tablename__ = "committee_members"
    __table_args__ = (
        Index("ix_committee_members_committee_designation", "committee_id", "designation"),
    )

    committee_id: Mapped[int] = mapped_column(ForeignKey("committees.id", ondelete="RESTRICT"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    gender: Mapped[str | None] = mapped_column(String(32))
    designation: Mapped[str | None] = mapped_column(String(80), index=True)
    mobile: Mapped[str | None] = mapped_column(String(24))
    notes: Mapped[str | None] = mapped_column(Text)

    committee: Mapped[Committee] = relationship(back_populates="members")
    visit_links: Mapped[list[AttendanceVisitMember]] = relationship(back_populates="committee_member")

    def __repr__(self) -> str:
        return f"<CommitteeMember {self.full_name!r}>"


class ActionPlan(LifecycleMixin, db.Model):
    """A single committee plan occurrence for one calendar month.

    Legacy seed/template rows can have ``plan_month`` set to NULL. Those rows are
    intentionally not executable by DAs and are ignored by monthly planning views.
    """

    __tablename__ = "action_plans"
    __table_args__ = (
        UniqueConstraint("committee_id", "plan_month", name="uq_action_plans_committee_month"),
        CheckConstraint(
            "plan_month IS NULL OR assigned_date IS NULL OR plan_type IS NOT NULL",
            name="ck_action_plans_assignment_pair",
        ),
        CheckConstraint(
            "plan_type IS NULL OR plan_type IN ('Attendance','Specials')",
            name="ck_action_plans_type",
        ),
        Index("ix_action_plans_committee_date", "committee_id", "assigned_date"),
        Index("ix_action_plans_month_type", "plan_month", "plan_type"),
    )

    committee_id: Mapped[int] = mapped_column(
        ForeignKey("committees.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    plan_month: Mapped[date | None] = mapped_column(Date, index=True)
    plan_type: Mapped[ActionPlanType | None] = mapped_column(
        Enum(ActionPlanType, **enum_options), nullable=True, index=True
    )
    assigned_date: Mapped[date | None] = mapped_column(Date, index=True)
    assigned_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    prepared_from_id: Mapped[int | None] = mapped_column(
        ForeignKey("action_plans.id", ondelete="SET NULL"), index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)

    committee: Mapped[Committee] = relationship(back_populates="action_plans")
    assigned_by: Mapped[User | None] = relationship(foreign_keys=[assigned_by_user_id])
    prepared_from: Mapped[ActionPlan | None] = relationship(
        remote_side="ActionPlan.id", foreign_keys=[prepared_from_id]
    )
    attendance_entry: Mapped[AttendanceEntry | None] = relationship(
        back_populates="action_plan", uselist=False
    )
    specials_entry: Mapped[SpecialsEntry | None] = relationship(
        back_populates="action_plan", uselist=False
    )

    @property
    def is_executable(self) -> bool:
        return self.plan_month is not None and self.plan_type is not None and self.assigned_date is not None

    def __repr__(self) -> str:
        month = self.plan_month.isoformat() if self.plan_month else "legacy"
        return f"<ActionPlan {self.title!r} month={month}>"

class User(UserMixin, LifecycleMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "(role = 'admin' AND pm_id IS NULL AND pc_id IS NULL AND da_id IS NULL) OR "
            "(role = 'pm' AND pm_id IS NOT NULL AND pc_id IS NULL AND da_id IS NULL) OR "
            "(role = 'pc' AND pm_id IS NULL AND pc_id IS NOT NULL AND da_id IS NULL) OR "
            "(role = 'da' AND pm_id IS NULL AND pc_id IS NULL AND da_id IS NOT NULL)",
            name="ck_users_role_profile",
        ),
    )

    email: Mapped[str | None] = mapped_column(String(254), unique=True, index=True)
    mobile: Mapped[str | None] = mapped_column(String(24), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, **enum_options), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    pm_id: Mapped[int | None] = mapped_column(ForeignKey("pms.id", ondelete="RESTRICT"), unique=True)
    pc_id: Mapped[int | None] = mapped_column(ForeignKey("pcs.id", ondelete="RESTRICT"), unique=True)
    da_id: Mapped[int | None] = mapped_column(ForeignKey("das.id", ondelete="RESTRICT"), unique=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    pm: Mapped[PM | None] = relationship(back_populates="users")
    pc: Mapped[PC | None] = relationship(back_populates="users")
    da: Mapped[DA | None] = relationship(back_populates="users")

    @property
    def is_active(self) -> bool:
        return self.is_enabled and not self.is_deleted

    @property
    def scope_profile_id(self) -> int | None:
        return {Role.PM: self.pm_id, Role.PC: self.pc_id, Role.DA: self.da_id}.get(self.role)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="scrypt")
        self.password_changed_at = utcnow()

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.display_name!r} {self.role.value}>"


class AttendanceEntry(LifecycleMixin, db.Model):
    __tablename__ = "attendance_entries"
    __table_args__ = (
        UniqueConstraint("action_plan_id", name="uq_attendance_action_plan"),
        UniqueConstraint("client_submission_id", name="uq_attendance_client_submission"),
        CheckConstraint("male_count >= 0 AND female_count >= 0", name="ck_attendance_nonnegative"),
        CheckConstraint("new_members_count >= 0", name="ck_attendance_new_members_nonnegative"),
        CheckConstraint("total_count = male_count + female_count", name="ck_attendance_total"),
        Index("ix_attendance_village_visit", "village_id", "visit_date"),
    )

    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id", ondelete="RESTRICT"), nullable=False, index=True)
    committee_id: Mapped[int] = mapped_column(ForeignKey("committees.id", ondelete="RESTRICT"), nullable=False, index=True)
    action_plan_id: Mapped[int] = mapped_column(ForeignKey("action_plans.id", ondelete="RESTRICT"), nullable=False, index=True)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    male_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    female_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_members_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    visit_designations: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSON), nullable=False, default=list)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus, **enum_options), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)
    photo_path: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    geolocation_source: Mapped[str | None] = mapped_column(String(32))
    submitted_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    client_submission_id: Mapped[str] = mapped_column(String(80), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    village: Mapped[Village] = relationship(back_populates="attendance_entries")
    committee: Mapped[Committee] = relationship(back_populates="attendance_entries")
    action_plan: Mapped[ActionPlan] = relationship(back_populates="attendance_entry")
    submitted_by: Mapped[User] = relationship(foreign_keys=[submitted_by_user_id])
    visited_members: Mapped[list[AttendanceVisitMember]] = relationship(
        back_populates="attendance_entry",
        cascade="all, delete-orphan",
        order_by="AttendanceVisitMember.designation_snapshot, AttendanceVisitMember.member_name_snapshot",
    )

    def __repr__(self) -> str:
        return f"<AttendanceEntry plan={self.action_plan_id} status={self.status.value}>"


class SpecialsEntry(LifecycleMixin, db.Model):
    __tablename__ = "specials_entries"
    __table_args__ = (
        UniqueConstraint("action_plan_id", name="uq_specials_action_plan"),
        UniqueConstraint("client_submission_id", name="uq_specials_client_submission"),
        CheckConstraint("participant_count >= 0", name="ck_specials_nonnegative"),
        CheckConstraint(
            "status IS NULL OR status IN ('Early','On-time','Postponed')",
            name="ck_specials_status",
        ),
        Index("ix_specials_village_event", "village_id", "event_date"),
    )

    village_id: Mapped[int] = mapped_column(
        ForeignKey("villages.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    committee_id: Mapped[int] = mapped_column(
        ForeignKey("committees.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Nullable only for backward compatibility with pre-rebuild rows. New submissions require it.
    action_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("action_plans.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(220))
    participant_count: Mapped[int] = mapped_column(Integer, nullable=False)
    scope: Mapped[SpecialScope] = mapped_column(
        Enum(SpecialScope, **enum_options), nullable=False, index=True
    )
    status: Mapped[AttendanceStatus | None] = mapped_column(
        Enum(AttendanceStatus, **enum_options), nullable=True, index=True
    )
    reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    photo_path: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    geolocation_source: Mapped[str | None] = mapped_column(String(32))
    submitted_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    client_submission_id: Mapped[str] = mapped_column(String(80), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    village: Mapped[Village] = relationship(back_populates="specials_entries")
    committee: Mapped[Committee] = relationship(back_populates="specials_entries")
    action_plan: Mapped[ActionPlan | None] = relationship(back_populates="specials_entry")
    submitted_by: Mapped[User] = relationship(foreign_keys=[submitted_by_user_id])

    def __repr__(self) -> str:
        return f"<SpecialsEntry village={self.village_id} participants={self.participant_count}>"


class AttendanceVisitMember(LifecycleMixin, db.Model):
    """Committee member selected under a DA visit designation.

    Snapshot columns preserve what was displayed at submission time even if the
    member's master-data name/designation changes later.
    """

    __tablename__ = "attendance_visit_members"
    __table_args__ = (
        UniqueConstraint(
            "attendance_entry_id",
            "committee_member_id",
            name="uq_attendance_visit_member",
        ),
        Index(
            "ix_attendance_visit_members_entry_designation",
            "attendance_entry_id",
            "designation_snapshot",
        ),
    )

    attendance_entry_id: Mapped[int] = mapped_column(
        ForeignKey("attendance_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    committee_member_id: Mapped[int] = mapped_column(
        ForeignKey("committee_members.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    member_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    designation_snapshot: Mapped[str] = mapped_column(String(80), nullable=False)
    gender_snapshot: Mapped[str | None] = mapped_column(String(32))

    attendance_entry: Mapped[AttendanceEntry] = relationship(back_populates="visited_members")
    committee_member: Mapped[CommitteeMember] = relationship(back_populates="visit_links")

    def __repr__(self) -> str:
        return f"<AttendanceVisitMember {self.member_name_snapshot!r} {self.designation_snapshot!r}>"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_actor_created", "actor_user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction, **enum_options), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)
    before_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    request_id: Mapped[str | None] = mapped_column(String(80))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    actor: Mapped[User | None] = relationship(foreign_keys=[actor_user_id])


class RecycleBin(db.Model):
    __tablename__ = "recycle_bin"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "restored_at", name="uq_recycle_entity_open"),
        Index("ix_recycle_purge_after", "purge_after"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(240))
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    deleted_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    purge_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    restored_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    deleted_by: Mapped[User | None] = relationship(foreign_keys=[deleted_by_user_id])
    restored_by: Mapped[User | None] = relationship(foreign_keys=[restored_by_user_id])


@event.listens_for(AttendanceEntry, "before_insert")
@event.listens_for(AttendanceEntry, "before_update")
def _attendance_total(_mapper, _connection, target: AttendanceEntry) -> None:
    target.total_count = int(target.male_count or 0) + int(target.female_count or 0)


@event.listens_for(AuditLog, "before_update")
@event.listens_for(AuditLog, "before_delete")
def _prevent_audit_mutation(_mapper, _connection, _target: AuditLog) -> None:
    raise ValueError("AuditLog rows are append-only.")
