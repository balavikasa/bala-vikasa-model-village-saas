#!/usr/bin/env python3
"""One-time migration from the accepted SQLite DB into an EMPTY PostgreSQL DB.

Safety properties:
- target must be PostgreSQL;
- target application tables must be empty;
- no destructive/merge mode is provided;
- Alembic version state is not copied;
- target inserts are performed in one transaction;
- PostgreSQL identity/serial sequences are reseeded after explicit ID inserts.

Run `flask --app wsgi db upgrade` on the target before this script.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import MetaData, create_engine, func, select, text

from app import create_app
from app.extensions import db


def chunks(rows, size: int = 500):
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        required=True,
        help="Path to the accepted SQLite model_village.db",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source_path = Path(args.source).expanduser().resolve()
    if not source_path.is_file():
        raise SystemExit(f"Source SQLite DB not found: {source_path}")

    source_engine = create_engine(f"sqlite:///{source_path.as_posix()}")
    source_meta = MetaData()
    source_meta.reflect(bind=source_engine)

    app = create_app()
    with app.app_context():
        target_engine = db.engine
        if target_engine.dialect.name != "postgresql":
            raise SystemExit(
                "Refusing to migrate: target DATABASE_URL must point to PostgreSQL."
            )

        target_tables = [
            table
            for table in db.metadata.sorted_tables
            if table.name != "alembic_version"
        ]

        nonempty: dict[str, int] = {}
        with target_engine.connect() as conn:
            for table in target_tables:
                count = conn.execute(
                    select(func.count()).select_from(table)
                ).scalar_one()
                if count:
                    nonempty[table.name] = count

        if nonempty:
            details = ", ".join(
                f"{name}={count}" for name, count in sorted(nonempty.items())
            )
            raise SystemExit(
                "Refusing to migrate into a non-empty PostgreSQL database. "
                f"Existing rows: {details}"
            )

        plan: list[tuple[str, int]] = []
        with source_engine.connect() as source_conn:
            for target_table in target_tables:
                source_table = source_meta.tables.get(target_table.name)
                if source_table is None:
                    plan.append((target_table.name, 0))
                    continue

                source_columns = set(source_table.c.keys())
                common = [
                    column.name
                    for column in target_table.columns
                    if column.name in source_columns
                ]
                rows = source_conn.execute(
                    select(*(source_table.c[name] for name in common))
                ).mappings().all()
                plan.append((target_table.name, len(rows)))

        print("Migration plan:")
        for name, count in plan:
            print(f"  {name}: {count} row(s)")

        if args.dry_run:
            print("Dry run complete. No rows were written.")
            return 0

        with (
            source_engine.connect() as source_conn,
            target_engine.begin() as target_conn,
        ):
            deferred_action_plan_links: list[tuple[int, int]] = []

            for target_table in target_tables:
                source_table = source_meta.tables.get(target_table.name)
                if source_table is None:
                    continue

                source_columns = set(source_table.c.keys())
                common = [
                    column.name
                    for column in target_table.columns
                    if column.name in source_columns
                ]

                statement = select(
                    *(source_table.c[name] for name in common)
                )
                if "id" in source_columns:
                    statement = statement.order_by(source_table.c.id)

                mappings = source_conn.execute(statement).mappings().all()

                payload: list[dict] = []
                for row in mappings:
                    item = {name: row[name] for name in common}

                    # action_plans.prepared_from_id is self-referential.
                    # Defer it until all action plans exist so SQLite row order
                    # cannot cause a PostgreSQL FK violation.
                    if (
                        target_table.name == "action_plans"
                        and item.get("prepared_from_id") is not None
                    ):
                        deferred_action_plan_links.append(
                            (int(item["id"]), int(item["prepared_from_id"]))
                        )
                        item["prepared_from_id"] = None

                    payload.append(item)

                for batch in chunks(payload):
                    if batch:
                        target_conn.execute(target_table.insert(), batch)

            if deferred_action_plan_links:
                action_plans = db.metadata.tables["action_plans"]
                for row_id, prepared_from_id in deferred_action_plan_links:
                    target_conn.execute(
                        action_plans.update()
                        .where(action_plans.c.id == row_id)
                        .values(prepared_from_id=prepared_from_id)
                    )

            # SQLite IDs are inserted explicitly. PostgreSQL sequences do not
            # automatically advance when explicit IDs are supplied, so reseed
            # every single-column integer primary-key sequence.
            for target_table in target_tables:
                primary_keys = list(target_table.primary_key.columns)
                if len(primary_keys) != 1:
                    continue
                pk = primary_keys[0]
                if not getattr(pk.type, "python_type", None) is int:
                    continue

                sequence_name = target_conn.execute(
                    text(
                        "SELECT pg_get_serial_sequence("
                        ":table_name, :column_name)"
                    ),
                    {
                        "table_name": target_table.name,
                        "column_name": pk.name,
                    },
                ).scalar_one_or_none()
                if not sequence_name:
                    continue

                max_id = target_conn.execute(
                    select(func.max(pk))
                ).scalar_one_or_none()

                if max_id is None:
                    target_conn.execute(
                        text(
                            "SELECT setval("
                            "to_regclass(:sequence_name), 1, false)"
                        ),
                        {"sequence_name": sequence_name},
                    )
                else:
                    target_conn.execute(
                        text(
                            "SELECT setval("
                            "to_regclass(:sequence_name), :value, true)"
                        ),
                        {
                            "sequence_name": sequence_name,
                            "value": int(max_id),
                        },
                    )

        print("SQLite -> PostgreSQL migration completed successfully.")
        print(
            "Reminder: copy the uploads directory separately if it contains "
            "field evidence."
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
