"""Optional Admin-managed Program Manager -> Project Coordinator assignment.

Existing PC accounts remain unassigned until Admin assigns a PM in Master Data.
No changes are made to login or reporting access scope by this migration.

Revision ID: 20261031_0005
Revises: 20261028_0004
"""
from alembic import op
import sqlalchemy as sa

revision = "20261031_0005"
down_revision = "20261028_0004"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("pcs") as batch:
        batch.add_column(sa.Column("pm_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_pcs_pm_id_pms", "pms", ["pm_id"], ["id"], ondelete="RESTRICT")
        batch.create_index("ix_pcs_pm_id", ["pm_id"])


def downgrade():
    with op.batch_alter_table("pcs") as batch:
        batch.drop_index("ix_pcs_pm_id")
        batch.drop_constraint("fk_pcs_pm_id_pms", type_="foreignkey")
        batch.drop_column("pm_id")
