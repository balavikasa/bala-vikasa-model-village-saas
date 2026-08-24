"""Monthly planning, visit-member reporting, and plan-linked specials.

Revision ID: 20260822_0002
Revises: 20260821_0001
Create Date: 2026-08-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260822_0002"
down_revision: Union[str, None] = "20260821_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _lifecycle_columns():
    return [
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    # Existing 351 seed rows remain as legacy/template rows with plan_month NULL.
    # New monthly occurrences are created by the planning workflow.
    with op.batch_alter_table("action_plans") as batch:
        batch.add_column(sa.Column("plan_month", sa.Date(), nullable=True))
        batch.add_column(sa.Column("plan_type", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("prepared_from_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_action_plans_prepared_from_id_action_plans",
            "action_plans",
            ["prepared_from_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_unique_constraint(
            "uq_action_plans_committee_month",
            ["committee_id", "plan_month"],
        )
        batch.create_check_constraint(
            "ck_action_plans_assignment_pair",
            "plan_month IS NULL OR assigned_date IS NULL OR plan_type IS NOT NULL",
        )
        batch.create_check_constraint(
            "ck_action_plans_type",
            "plan_type IS NULL OR plan_type IN ('Attendance','Specials')",
        )

    op.create_index("ix_action_plans_plan_month", "action_plans", ["plan_month"])
    op.create_index("ix_action_plans_plan_type", "action_plans", ["plan_type"])
    op.create_index("ix_action_plans_prepared_from_id", "action_plans", ["prepared_from_id"])
    op.create_index("ix_action_plans_month_type", "action_plans", ["plan_month", "plan_type"])

    with op.batch_alter_table("attendance_entries") as batch:
        batch.add_column(
            sa.Column("new_members_count", sa.Integer(), nullable=False, server_default=sa.text("0"))
        )
        batch.create_check_constraint(
            "ck_attendance_new_members_nonnegative",
            "new_members_count >= 0",
        )

    with op.batch_alter_table("specials_entries") as batch:
        batch.add_column(sa.Column("action_plan_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("status", sa.String(length=16), nullable=True))
        batch.add_column(sa.Column("reason", sa.Text(), nullable=True))
        batch.create_foreign_key(
            "fk_specials_entries_action_plan_id_action_plans",
            "action_plans",
            ["action_plan_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_unique_constraint("uq_specials_action_plan", ["action_plan_id"])
        batch.create_check_constraint(
            "ck_specials_status",
            "status IS NULL OR status IN ('Early','On-time','Postponed')",
        )

    op.create_index("ix_specials_entries_action_plan_id", "specials_entries", ["action_plan_id"])
    op.create_index("ix_specials_entries_status", "specials_entries", ["status"])

    op.create_table(
        "attendance_visit_members",
        *_lifecycle_columns(),
        sa.Column(
            "attendance_entry_id",
            sa.Integer(),
            sa.ForeignKey("attendance_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "committee_member_id",
            sa.Integer(),
            sa.ForeignKey("committee_members.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("member_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("designation_snapshot", sa.String(length=80), nullable=False),
        sa.Column("gender_snapshot", sa.String(length=32), nullable=True),
        sa.UniqueConstraint(
            "attendance_entry_id",
            "committee_member_id",
            name="uq_attendance_visit_member",
        ),
    )
    op.create_index(
        "ix_attendance_visit_members_is_enabled",
        "attendance_visit_members",
        ["is_enabled"],
    )
    op.create_index(
        "ix_attendance_visit_members_is_deleted",
        "attendance_visit_members",
        ["is_deleted"],
    )
    op.create_index(
        "ix_attendance_visit_members_attendance_entry_id",
        "attendance_visit_members",
        ["attendance_entry_id"],
    )
    op.create_index(
        "ix_attendance_visit_members_committee_member_id",
        "attendance_visit_members",
        ["committee_member_id"],
    )
    op.create_index(
        "ix_attendance_visit_members_entry_designation",
        "attendance_visit_members",
        ["attendance_entry_id", "designation_snapshot"],
    )


def downgrade() -> None:
    op.drop_table("attendance_visit_members")

    op.drop_index("ix_specials_entries_status", table_name="specials_entries")
    op.drop_index("ix_specials_entries_action_plan_id", table_name="specials_entries")
    with op.batch_alter_table("specials_entries") as batch:
        batch.drop_constraint("ck_specials_status", type_="check")
        batch.drop_constraint("uq_specials_action_plan", type_="unique")
        batch.drop_constraint(
            "fk_specials_entries_action_plan_id_action_plans",
            type_="foreignkey",
        )
        batch.drop_column("reason")
        batch.drop_column("status")
        batch.drop_column("action_plan_id")

    with op.batch_alter_table("attendance_entries") as batch:
        batch.drop_constraint("ck_attendance_new_members_nonnegative", type_="check")
        batch.drop_column("new_members_count")

    op.drop_index("ix_action_plans_month_type", table_name="action_plans")
    op.drop_index("ix_action_plans_prepared_from_id", table_name="action_plans")
    op.drop_index("ix_action_plans_plan_type", table_name="action_plans")
    op.drop_index("ix_action_plans_plan_month", table_name="action_plans")
    with op.batch_alter_table("action_plans") as batch:
        batch.drop_constraint("ck_action_plans_type", type_="check")
        batch.drop_constraint("ck_action_plans_assignment_pair", type_="check")
        batch.drop_constraint("uq_action_plans_committee_month", type_="unique")
        batch.drop_constraint(
            "fk_action_plans_prepared_from_id_action_plans",
            type_="foreignkey",
        )
        batch.drop_column("prepared_from_id")
        batch.drop_column("plan_type")
        batch.drop_column("plan_month")
