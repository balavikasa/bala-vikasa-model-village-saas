from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import (
    DA,
    PC,
    PM,
    ActionPlan,
    AttendanceEntry,
    AuditAction,
    AuditLog,
    Committee,
    CommitteeMember,
    RecycleBin,
    Role,
    SpecialsEntry,
    User,
    Village,
)
from .services.files import delete_photo
from .services.workbook import WorkbookImportError, database_counts, import_workbook

PURGE_MODELS = {
    model.__name__: model
    for model in (
        PM,
        PC,
        DA,
        Village,
        Committee,
        CommitteeMember,
        ActionPlan,
        AttendanceEntry,
        SpecialsEntry,
        User,
    )
}


def register_commands(app) -> None:
    app.cli.add_command(seed_admin)
    app.cli.add_command(import_master_data)
    app.cli.add_command(master_data_counts)
    app.cli.add_command(backfill_village_coordinates)
    app.cli.add_command(purge_recycle_bin)


@click.command("seed-admin")
@click.option("--email", prompt=True, help="Administrator email address.")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--name", default="Program Administrator", show_default=True)
@with_appcontext
def seed_admin(email: str, password: str, name: str) -> None:
    """Create the first administrator account."""

    email = email.strip().casefold()
    if len(password) < 12:
        raise click.ClickException("Administrator passwords must contain at least 12 characters.")
    existing = db.session.scalar(db.select(User).where(User.email == email))
    if existing:
        raise click.ClickException("A user with that email already exists.")
    user = User(display_name=name.strip(), email=email, role=Role.ADMIN)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Created administrator {email}.")


@click.command("import-master-data")
@click.argument("workbook", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--mapping", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--replace", is_flag=True, help="Replace master data after safety checks.")
@click.option(
    "--confirm-replace",
    is_flag=True,
    help="Required with --replace to acknowledge destructive replacement.",
)
@with_appcontext
def import_master_data(workbook: Path, mapping: Path | None, replace: bool, confirm_replace: bool) -> None:
    """Atomically import the program master-data workbook."""

    if replace and not confirm_replace:
        raise click.ClickException("--replace also requires --confirm-replace.")
    try:
        result = import_workbook(workbook, replace=replace, mapping_path=mapping)
    except WorkbookImportError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, indent=2, default=str))


@click.command("master-data-counts")
@with_appcontext
def master_data_counts() -> None:
    """Print current non-deleted master-data counts."""

    click.echo(json.dumps(database_counts(), indent=2))


def _location_key(value: str | None) -> str:
    return "".join(ch for ch in (value or "").casefold() if ch.isalnum())


@click.command("backfill-village-coordinates")
@click.option(
    "--source",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Coordinate JSON. Defaults to data/village-coordinates.prototype.json.",
)
@click.option("--force", is_flag=True, help="Replace coordinates that are already populated.")
@with_appcontext
def backfill_village_coordinates(source: Path | None, force: bool) -> None:
    """Fill missing Village coordinates from the approved prototype mapping.

    These coordinates came from the approved UI prototype rather than the original
    master workbook, so the command is explicit rather than silently running in a
    schema migration.
    """

    source = source or (Path(current_app.root_path).parent / "data" / "village-coordinates.prototype.json")
    try:
        records = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise click.ClickException(f"Could not read coordinate source: {source}") from exc

    by_name: dict[str, list[dict]] = {}
    for record in records:
        by_name.setdefault(_location_key(record.get("name")), []).append(record)

    updated = skipped = 0
    unmatched: list[str] = []
    ambiguous: list[str] = []
    villages = db.session.scalars(
        db.select(Village).where(Village.is_deleted.is_(False)).order_by(Village.name)
    ).all()

    for village in villages:
        matches = by_name.get(_location_key(village.name), [])
        if not matches:
            unmatched.append(village.name)
            continue
        if len(matches) > 1:
            # Prefer an exact district/mandal match when a name is duplicated.
            narrowed = [
                item
                for item in matches
                if _location_key(item.get("district")) == _location_key(village.district)
                and _location_key(item.get("mandal")) == _location_key(village.mandal)
            ]
            matches = narrowed
        if len(matches) != 1:
            ambiguous.append(village.name)
            continue

        if not force and village.latitude is not None and village.longitude is not None:
            skipped += 1
            continue

        item = matches[0]
        latitude = item.get("latitude")
        longitude = item.get("longitude")
        if latitude is None or longitude is None or not (-90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180):
            unmatched.append(village.name)
            continue
        village.latitude = float(latitude)
        village.longitude = float(longitude)
        updated += 1

    db.session.commit()
    click.echo(
        json.dumps(
            {
                "source": str(source),
                "updated": updated,
                "skipped_existing": skipped,
                "unmatched": unmatched,
                "ambiguous": ambiguous,
            },
            indent=2,
        )
    )


@click.command("purge-recycle-bin")
@click.option("--dry-run", is_flag=True, help="List eligible records without deleting them.")
@with_appcontext
def purge_recycle_bin(dry_run: bool) -> None:
    """Permanently purge soft-deleted records after the retention period."""

    now = datetime.now(UTC)
    rows = db.session.scalars(
        db.select(RecycleBin)
        .where(
            RecycleBin.restored_at.is_(None),
            RecycleBin.purge_after <= now,
        )
        .order_by(RecycleBin.purge_after)
    ).all()
    if dry_run:
        click.echo(json.dumps([
            {"id": row.id, "entity_type": row.entity_type, "entity_id": row.entity_id, "purge_after": row.purge_after.isoformat()}
            for row in rows
        ], indent=2))
        return

    purged, deferred = 0, []
    # Leaf entities first reduces FK conflicts when multiple related rows expire together.
    priority = {
        "AttendanceEntry": 0,
        "SpecialsEntry": 0,
        "CommitteeMember": 0,
        "ActionPlan": 1,
        "Committee": 2,
        "Village": 3,
        "DA": 4,
        "PC": 5,
        "PM": 5,
        "User": 6,
    }
    rows.sort(key=lambda row: priority.get(row.entity_type, 99))

    for row in rows:
        model = PURGE_MODELS.get(row.entity_type)
        if model is None:
            deferred.append({"bin_id": row.id, "reason": "unknown model"})
            continue
        try:
            with db.session.begin_nested():
                record = db.session.get(model, row.entity_id)
                if record is not None:
                    if not getattr(record, "is_deleted", False):
                        raise ValueError("underlying record is not deleted")
                    if isinstance(record, (AttendanceEntry, SpecialsEntry)):
                        delete_photo(record.photo_path)
                    db.session.add(
                        AuditLog(
                            actor_user_id=None,
                            action=AuditAction.PURGE,
                            entity_type=row.entity_type,
                            entity_id=row.entity_id,
                            before_json=row.snapshot_json,
                        )
                    )
                    db.session.delete(record)
                db.session.delete(row)
                db.session.flush()
            purged += 1
        except (IntegrityError, ValueError) as exc:
            deferred.append({"bin_id": row.id, "reason": str(exc)})
    db.session.commit()
    click.echo(json.dumps({"purged": purged, "deferred": deferred}, indent=2))
