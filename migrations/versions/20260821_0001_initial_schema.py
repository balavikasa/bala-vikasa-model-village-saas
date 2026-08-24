"""Initial normalized Model Village schema.

Revision ID: 20260821_0001
Revises:
Create Date: 2026-08-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260821_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def lifecycle_columns():
    return [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def lifecycle_indexes(table):
    op.create_index(f"ix_{table}_is_enabled", table, ["is_enabled"])
    op.create_index(f"ix_{table}_is_deleted", table, ["is_deleted"])


def upgrade() -> None:
    op.create_table(
        "pms",
        *lifecycle_columns(),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(254), nullable=True, unique=True),
        sa.Column("mobile", sa.String(24), nullable=True, unique=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    lifecycle_indexes("pms")
    op.create_index("ix_pms_full_name", "pms", ["full_name"])

    op.create_table(
        "pcs",
        *lifecycle_columns(),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("cluster", sa.String(4), nullable=False),
        sa.Column("email", sa.String(254), nullable=True, unique=True),
        sa.Column("mobile", sa.String(24), nullable=True, unique=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("cluster IN ('CSRB','PDTC')", name="ck_pcs_cluster"),
    )
    lifecycle_indexes("pcs")
    op.create_index("ix_pcs_full_name", "pcs", ["full_name"])
    op.create_index("ix_pcs_cluster", "pcs", ["cluster"])

    op.create_table(
        "das",
        *lifecycle_columns(),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("pc_id", sa.Integer(), sa.ForeignKey("pcs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("email", sa.String(254), nullable=True, unique=True),
        sa.Column("mobile", sa.String(24), nullable=True, unique=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    lifecycle_indexes("das")
    op.create_index("ix_das_full_name", "das", ["full_name"])
    op.create_index("ix_das_pc_id", "das", ["pc_id"])

    op.create_table(
        "villages",
        *lifecycle_columns(),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("code", sa.String(40), nullable=True, unique=True),
        sa.Column("gp_name", sa.String(160), nullable=True),
        sa.Column("district", sa.String(120), nullable=True),
        sa.Column("mandal", sa.String(120), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("da_id", sa.Integer(), sa.ForeignKey("das.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("da_id", "name", name="uq_villages_da_name"),
    )
    lifecycle_indexes("villages")
    op.create_index("ix_villages_name", "villages", ["name"])
    op.create_index("ix_villages_da_id", "villages", ["da_id"])
    op.create_index("ix_villages_coordinates", "villages", ["latitude", "longitude"])

    op.create_table(
        "committees",
        *lifecycle_columns(),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("committee_type", sa.String(100), nullable=True),
        sa.Column("village_id", sa.Integer(), sa.ForeignKey("villages.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("village_id", "name", name="uq_committees_village_name"),
    )
    lifecycle_indexes("committees")
    op.create_index("ix_committees_name", "committees", ["name"])
    op.create_index("ix_committees_committee_type", "committees", ["committee_type"])
    op.create_index("ix_committees_village_id", "committees", ["village_id"])

    op.create_table(
        "committee_members",
        *lifecycle_columns(),
        sa.Column("committee_id", sa.Integer(), sa.ForeignKey("committees.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("gender", sa.String(32), nullable=True),
        sa.Column("designation", sa.String(80), nullable=True),
        sa.Column("mobile", sa.String(24), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    lifecycle_indexes("committee_members")
    op.create_index("ix_committee_members_committee_id", "committee_members", ["committee_id"])
    op.create_index("ix_committee_members_full_name", "committee_members", ["full_name"])
    op.create_index("ix_committee_members_designation", "committee_members", ["designation"])
    op.create_index("ix_committee_members_committee_designation", "committee_members", ["committee_id", "designation"])

    op.create_table(
        "users",
        *lifecycle_columns(),
        sa.Column("email", sa.String(254), nullable=True, unique=True),
        sa.Column("mobile", sa.String(24), nullable=True, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(8), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("pm_id", sa.Integer(), sa.ForeignKey("pms.id", ondelete="RESTRICT"), nullable=True, unique=True),
        sa.Column("pc_id", sa.Integer(), sa.ForeignKey("pcs.id", ondelete="RESTRICT"), nullable=True, unique=True),
        sa.Column("da_id", sa.Integer(), sa.ForeignKey("das.id", ondelete="RESTRICT"), nullable=True, unique=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(role = 'admin' AND pm_id IS NULL AND pc_id IS NULL AND da_id IS NULL) OR "
            "(role = 'pm' AND pm_id IS NOT NULL AND pc_id IS NULL AND da_id IS NULL) OR "
            "(role = 'pc' AND pm_id IS NULL AND pc_id IS NOT NULL AND da_id IS NULL) OR "
            "(role = 'da' AND pm_id IS NULL AND pc_id IS NULL AND da_id IS NOT NULL)",
            name="ck_users_role_profile",
        ),
        sa.CheckConstraint("role IN ('admin','pm','pc','da')", name="ck_users_role"),
    )
    lifecycle_indexes("users")
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_mobile", "users", ["mobile"])
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "action_plans",
        *lifecycle_columns(),
        sa.Column("committee_id", sa.Integer(), sa.ForeignKey("committees.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assigned_date", sa.Date(), nullable=True),
        sa.Column("assigned_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    lifecycle_indexes("action_plans")
    op.create_index("ix_action_plans_committee_id", "action_plans", ["committee_id"])
    op.create_index("ix_action_plans_title", "action_plans", ["title"])
    op.create_index("ix_action_plans_assigned_date", "action_plans", ["assigned_date"])
    op.create_index("ix_action_plans_assigned_by_user_id", "action_plans", ["assigned_by_user_id"])
    op.create_index("ix_action_plans_committee_date", "action_plans", ["committee_id", "assigned_date"])

    op.create_table(
        "attendance_entries",
        *lifecycle_columns(),
        sa.Column("village_id", sa.Integer(), sa.ForeignKey("villages.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("committee_id", sa.Integer(), sa.ForeignKey("committees.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action_plan_id", sa.Integer(), sa.ForeignKey("action_plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("male_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("female_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("visit_designations", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("photo_path", sa.String(500), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("geolocation_source", sa.String(32), nullable=True),
        sa.Column("submitted_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_submission_id", sa.String(80), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("action_plan_id", name="uq_attendance_action_plan"),
        sa.UniqueConstraint("client_submission_id", name="uq_attendance_client_submission"),
        sa.CheckConstraint("male_count >= 0 AND female_count >= 0", name="ck_attendance_nonnegative"),
        sa.CheckConstraint("total_count = male_count + female_count", name="ck_attendance_total"),
        sa.CheckConstraint("status IN ('Early','On-time','Postponed')", name="ck_attendance_status"),
    )
    lifecycle_indexes("attendance_entries")
    for column in ("village_id", "committee_id", "action_plan_id", "visit_date", "status", "submitted_by_user_id"):
        op.create_index(f"ix_attendance_entries_{column}", "attendance_entries", [column])
    op.create_index("ix_attendance_village_visit", "attendance_entries", ["village_id", "visit_date"])

    op.create_table(
        "specials_entries",
        *lifecycle_columns(),
        sa.Column("village_id", sa.Integer(), sa.ForeignKey("villages.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("committee_id", sa.Integer(), sa.ForeignKey("committees.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(220), nullable=True),
        sa.Column("participant_count", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("photo_path", sa.String(500), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("geolocation_source", sa.String(32), nullable=True),
        sa.Column("submitted_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_submission_id", sa.String(80), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("client_submission_id", name="uq_specials_client_submission"),
        sa.CheckConstraint("participant_count >= 0", name="ck_specials_nonnegative"),
        sa.CheckConstraint("scope IN ('Under GP','Under VDC')", name="ck_specials_scope"),
    )
    lifecycle_indexes("specials_entries")
    for column in ("village_id", "committee_id", "event_date", "scope", "submitted_by_user_id"):
        op.create_index(f"ix_specials_entries_{column}", "specials_entries", [column])
    op.create_index("ix_specials_village_event", "specials_entries", ["village_id", "event_date"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(80), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_actor_created", "audit_logs", ["actor_user_id", "created_at"])

    op.create_table(
        "recycle_bin",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(240), nullable=True),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("deleted_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("restored_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("entity_type", "entity_id", "restored_at", name="uq_recycle_entity_open"),
    )
    op.create_index("ix_recycle_bin_entity_type", "recycle_bin", ["entity_type"])
    op.create_index("ix_recycle_bin_entity_id", "recycle_bin", ["entity_id"])
    op.create_index("ix_recycle_purge_after", "recycle_bin", ["purge_after"])


def downgrade() -> None:
    op.drop_table("recycle_bin")
    op.drop_table("audit_logs")
    op.drop_table("specials_entries")
    op.drop_table("attendance_entries")
    op.drop_table("action_plans")
    op.drop_table("users")
    op.drop_table("committee_members")
    op.drop_table("committees")
    op.drop_table("villages")
    op.drop_table("das")
    op.drop_table("pcs")
    op.drop_table("pms")
