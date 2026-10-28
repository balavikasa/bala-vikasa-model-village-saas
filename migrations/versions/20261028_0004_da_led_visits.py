"""DA-led village visits, no mandatory committee action plan.

Revision ID: 20261028_0004
Revises: 20261027_0003
"""
from alembic import op
import sqlalchemy as sa

revision = "20261028_0004"
down_revision = "20261027_0003"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("attendance_entries") as batch:
        batch.alter_column("action_plan_id", existing_type=sa.Integer(), nullable=True)
    with op.batch_alter_table("village_attendance_visits") as batch:
        batch.add_column(sa.Column("visit_month", sa.Date(), nullable=True))
        batch.add_column(sa.Column("new_members_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("outside_assignment", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_index("uq_active_village_visit_month", "village_attendance_visits",
                    ["village_id", "visit_month"], unique=True,
                    postgresql_where=sa.text("is_deleted = false"),
                    sqlite_where=sa.text("is_deleted = 0"))

def downgrade():
    raise RuntimeError("A destructive downgrade is not supported: preserve DA-led attendance records.")
