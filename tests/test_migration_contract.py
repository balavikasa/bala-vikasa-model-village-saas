
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_initial_migration_contains_all_tables():
    migrations = list((ROOT / "migrations" / "versions").glob("*.py"))
    assert migrations
    source = "\n".join(path.read_text(encoding="utf-8") for path in migrations)
    for table in (
        "pms", "pcs", "das", "villages", "committees", "committee_members",
        "action_plans", "attendance_entries", "specials_entries", "attendance_visit_members", "users",
        "audit_logs", "recycle_bin",
    ):
        assert table in source


def test_migration_has_upgrade_and_downgrade():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "migrations" / "versions").glob("*.py")
    )
    assert "def upgrade" in source
    assert "def downgrade" in source
