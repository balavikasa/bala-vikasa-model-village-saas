"""One photo / one GPS per village attendance submission; historical rows untouched.

Revision ID: 20261027_0003
Revises: 20260822_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "20261027_0003"
down_revision = "20260822_0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "village_attendance_visits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("village_id", sa.Integer(), sa.ForeignKey("villages.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("photo_path", sa.String(500), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("geolocation_source", sa.String(32), nullable=False),
        sa.Column("remarks", sa.Text()),
        sa.Column("client_submission_id", sa.String(80), nullable=False),
        sa.Column("submitted_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("client_submission_id", name="uq_village_visit_submission"),
    )
    op.create_index("ix_village_attendance_visits_is_enabled", "village_attendance_visits", ["is_enabled"])
    op.create_index("ix_village_attendance_visits_is_deleted", "village_attendance_visits", ["is_deleted"])
    op.create_index("ix_village_attendance_visits_village_id", "village_attendance_visits", ["village_id"])
    op.create_index("ix_village_attendance_visits_submitted_by_user_id", "village_attendance_visits", ["submitted_by_user_id"])
    op.create_index("ix_village_attendance_visit_date", "village_attendance_visits", ["village_id", "visit_date"])
    with op.batch_alter_table("attendance_entries") as batch:
        batch.add_column(sa.Column("village_visit_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_attendance_village_visit", "village_attendance_visits", ["village_visit_id"], ["id"], ondelete="RESTRICT")
        batch.create_index("ix_attendance_entries_village_visit_id", ["village_visit_id"])


def downgrade():
    with op.batch_alter_table("attendance_entries") as batch:
        batch.drop_index("ix_attendance_entries_village_visit_id")
        batch.drop_constraint("fk_attendance_village_visit", type_="foreignkey")
        batch.drop_column("village_visit_id")
    op.drop_table("village_attendance_visits")
