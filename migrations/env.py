from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from flask import current_app

config = context.config
if config.config_file_name is not None and Path(config.config_file_name).exists():
    fileConfig(config.config_file_name)

target_db = current_app.extensions["migrate"].db
target_metadata = target_db.metadata


def get_engine():
    try:
        return target_db.get_engine()
    except (TypeError, AttributeError):
        return target_db.engine


def get_url():
    return str(get_engine().url).replace("%", "%%")


config.set_main_option("sqlalchemy.url", get_url())


def run_migrations_offline():
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = get_engine()
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
