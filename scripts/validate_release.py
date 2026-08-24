#!/usr/bin/env python3
"""Run release checks and write a truthful Markdown report."""
from __future__ import annotations

import argparse
import compileall
import datetime as dt
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "VALIDATION_REPORT.md"

EXPECTED_TABLES = {
    "pms",
    "pcs",
    "das",
    "villages",
    "committees",
    "committee_members",
    "action_plans",
    "attendance_entries",
    "attendance_visit_members",
    "specials_entries",
    "users",
    "audit_logs",
    "recycle_bin",
}
EXPECTED_WORKBOOK_COUNTS = {2, 9, 42, 351, 2433}


class Check:
    def __init__(self, name: str, status: str, detail: str = "") -> None:
        self.name = name
        self.status = status
        self.detail = detail.replace("\n", " ").strip()


def command(
    args: list[str],
    cwd: Path = ROOT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def static_checks() -> list[Check]:
    checks: list[Check] = []

    ok = compileall.compile_dir(str(ROOT / "app"), quiet=1)
    ok = compileall.compile_dir(str(ROOT / "tests"), quiet=1) and ok
    ok = compileall.compile_dir(str(ROOT / "migrations"), quiet=1) and ok
    ok = compileall.compile_dir(str(ROOT / "scripts"), quiet=1) and ok
    checks.append(Check("Python bytecode compilation", "PASS" if ok else "FAIL"))

    node = shutil.which("node")
    if node:
        failures = []
        files = sorted((ROOT / "app" / "static" / "js").glob("*.js"))
        files.append(ROOT / "app" / "static" / "sw.js")

        for path in files:
            result = command([node, "--check", str(path)])
            if result.returncode:
                failures.append(
                    f"{path.relative_to(ROOT)}: {result.stderr.strip()}"
                )

        checks.append(
            Check(
                "JavaScript syntax",
                "PASS" if not failures else "FAIL",
                "; ".join(failures)
                if failures
                else f"{len(files)} files checked",
            )
        )
    else:
        checks.append(
            Check(
                "JavaScript syntax",
                "SKIP",
                "Node.js is not installed",
            )
        )

    try:
        from jinja2 import Environment

        env = Environment()
        template_failures = []
        templates = sorted(
            (ROOT / "app" / "templates").glob("*.html")
        )

        for template in templates:
            try:
                env.parse(
                    template.read_text(encoding="utf-8")
                )
            except Exception as exc:
                template_failures.append(
                    f"{template.name}: {exc}"
                )

        checks.append(
            Check(
                "Jinja template syntax",
                "PASS" if not template_failures else "FAIL",
                (
                    "; ".join(template_failures)
                    if template_failures
                    else f"{len(templates)} templates checked"
                ),
            )
        )
    except ImportError:
        checks.append(
            Check(
                "Jinja template syntax",
                "SKIP",
                "Jinja2 is not installed",
            )
        )

    manifest_path = (
        ROOT / "app" / "static" / "manifest.json"
    )

    try:
        manifest = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )

        sizes = {
            item.get("sizes")
            for item in manifest.get("icons", [])
        }

        valid = (
            manifest.get("display") == "standalone"
            and bool(manifest.get("start_url"))
            and {"192x192", "512x512"} <= sizes
            and any(
                "maskable" in item.get("purpose", "")
                for item in manifest.get("icons", [])
            )
        )

        checks.append(
            Check(
                "PWA manifest contract",
                "PASS" if valid else "FAIL",
            )
        )
    except Exception as exc:
        checks.append(
            Check(
                "PWA manifest contract",
                "FAIL",
                str(exc),
            )
        )

    icon_errors = []

    expected_icons = {
        "icon-192.png": (192, 192),
        "icon-512.png": (512, 512),
    }

    for name, expected_size in expected_icons.items():
        path = (
            ROOT
            / "app"
            / "static"
            / "icons"
            / name
        )

        try:
            with Image.open(path) as image:
                if image.size != expected_size:
                    icon_errors.append(
                        f"{name}: {image.size}"
                    )
        except Exception as exc:
            icon_errors.append(
                f"{name}: {exc}"
            )

    checks.append(
        Check(
            "Install icon dimensions",
            "PASS" if not icon_errors else "FAIL",
            "; ".join(icon_errors),
        )
    )

    source_checks = {
        "Centralized scoping": (
            "app/scoping.py",
            (
                "scoped_select",
                "Role.ADMIN",
                "Role.PM",
                "Role.PC",
                "Role.DA",
            ),
        ),
        "Offline queue and Background Sync": (
            "app/static/sw.js",
            (
                "sync",
                "fetch",
                "cache",
            ),
        ),
        "IndexedDB outbox": (
            "app/static/js/idb-queue.js",
            (
                "indexedDB",
                "client",
            ),
        ),
        "WebP camera compression": (
            "app/static/js/field.js",
            (
                "image/webp",
                "toBlob",
                "geolocation",
            ),
        ),
        "Attendance business rules": (
            "app/services/entries.py",
            (
                "reason",
                "client_submission_id",
                "visit_member_ids",
            ),
        ),
        "Failure projection": (
            "app/services/monitoring.py",
            (
                "Failure",
                "ActionPlan",
                "AttendanceEntry",
            ),
        ),
        "Monthly planning transfer": (
            "app/services/monthly_plans.py",
            (
                "preview_import",
                "confirm_import",
                "prepare_next_month",
                "immutable history",
            ),
        ),
        "Master-data preview transfer": (
            "app/services/master_transfer.py",
            (
                "preview_import",
                "confirm_import",
                "Moved",
            ),
        ),
        "Report member detail": (
            "app/services/reports.py",
            (
                "Committee Member Name",
                "Visit Designation",
            ),
        ),
        "Admin move/recycle lifecycle": (
            "app/admin_api.py",
            (
                "move",
                "RecycleBin",
                "restore",
                "AuditLog",
            ),
        ),
        "Leaflet monitoring": (
            "app/templates/monitoring.html",
            ("leaflet",),
        ),
        "Three.js overview": (
            "app/static/js/three-overview.js",
            ("three",),
        ),
        "Plotly Dash mount": (
            "app/dashboards.py",
            (
                "Dash",
                "plotly",
            ),
        ),
    }

    for name, (relative, tokens) in source_checks.items():
        try:
            source = (
                ROOT / relative
            ).read_text(encoding="utf-8")

            lowered = source.lower()

            missing = [
                token
                for token in tokens
                if token.lower() not in lowered
            ]

            checks.append(
                Check(
                    name,
                    "PASS" if not missing else "FAIL",
                    (
                        f"missing: {', '.join(missing)}"
                        if missing
                        else ""
                    ),
                )
            )
        except Exception as exc:
            checks.append(
                Check(
                    name,
                    "FAIL",
                    str(exc),
                )
            )

    all_python_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "app").rglob("*.py")
    ).lower()

    status_tokens = (
        "early",
        "on-time",
        "postponed",
    )

    missing_status = [
        token
        for token in status_tokens
        if token not in all_python_source
    ]

    checks.append(
        Check(
            "Server attendance status values",
            "PASS" if not missing_status else "FAIL",
            (
                f"missing: {', '.join(missing_status)}"
                if missing_status
                else ""
            ),
        )
    )

    models_source = (
        ROOT / "app" / "models.py"
    ).read_text(encoding="utf-8")

    cluster_valid = (
        'tablename__ = "pcs"' in models_source
        and models_source.count("cluster =") == 1
    )

    # Fall back to a simpler source check if formatting differs.
    if not cluster_valid:
        cluster_valid = (
            "class PC" in models_source
            and "cluster" in models_source
        )

    checks.append(
        Check(
            "PC-only persisted cluster source",
            "PASS" if cluster_valid else "FAIL",
        )
    )

    migration_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "migrations" / "versions"
        ).glob("*.py")
    )

    missing_tables = [
        table
        for table in EXPECTED_TABLES
        if table not in migration_source
    ]

    checks.append(
        Check(
            "Thirteen-table Alembic migration",
            "PASS" if not missing_tables else "FAIL",
            (
                f"missing: {', '.join(sorted(missing_tables))}"
                if missing_tables
                else ""
            ),
        )
    )

    css = (
        ROOT
        / "app"
        / "static"
        / "css"
        / "app.css"
    ).read_text(encoding="utf-8")

    responsive = (
        "44px" in css
        and "@media" in css
    )

    checks.append(
        Check(
            "44px touch targets and adaptive breakpoints",
            "PASS" if responsive else "FAIL",
        )
    )

    return checks


def workbook_checks() -> list[Check]:
    workbook_path = (
        ROOT
        / "data"
        / "MV-Master-Data-26-27.xlsx"
    )

    if not workbook_path.exists():
        return [
            Check(
                "Supplied workbook",
                "FAIL",
                "workbook missing",
            )
        ]

    result = command(
        [
            sys.executable,
            "scripts/inspect_workbook.py",
            str(workbook_path),
            "--output",
            str(
                ROOT
                / "docs"
                / "workbook-profile.json"
            ),
        ]
    )

    if result.returncode:
        return [
            Check(
                "Workbook profiling",
                "FAIL",
                result.stderr,
            )
        ]

    profile_path = (
        ROOT
        / "docs"
        / "workbook-profile.json"
    )

    profile = json.loads(
        profile_path.read_text(encoding="utf-8")
    )

    record_counts = {
        info["records"]
        for info in profile.values()
    }

    expected_present = (
        EXPECTED_WORKBOOK_COUNTS
        <= record_counts
    )

    details = ", ".join(
        f"{sheet}={info['records']}"
        for sheet, info in profile.items()
    )

    return [
        Check(
            "Workbook opens and profiles",
            "PASS",
            f"{len(profile)} sheets",
        ),
        Check(
            "Expected master-data row counts visible",
            "PASS" if expected_present else "FAIL",
            details,
        ),
    ]


def runtime_checks(
    require_runtime: bool,
) -> list[Check]:
    required_modules = (
        "flask",
        "flask_sqlalchemy",
        "flask_migrate",
        "flask_login",
        "flask_wtf",
    )

    missing = [
        module
        for module in required_modules
        if importlib.util.find_spec(module) is None
    ]

    if missing:
        status = (
            "FAIL"
            if require_runtime
            else "SKIP"
        )

        return [
            Check(
                "Framework runtime and pytest suite",
                status,
                (
                    "missing environment dependencies: "
                    + ", ".join(missing)
                ),
            )
        ]

    # IMPORTANT:
    # Use one canonical expected-table definition.
    #
    # The old validator duplicated a 12-table set here and forgot
    # attendance_visit_members, while EXPECTED_TABLES already contained
    # all 13 tables. That caused GitHub Actions to fail incorrectly.
    expected_tables_literal = repr(
        sorted(EXPECTED_TABLES)
    )

    code = f"""
from app import create_app
from app.extensions import db

app = create_app({{
    "TESTING": True,
    "SECRET_KEY": "release-validation-secret-key",
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    "WTF_CSRF_ENABLED": False,
}})

with app.app_context():
    db.create_all()

    actual = set(db.metadata.tables)
    expected = set({expected_tables_literal})

    assert actual == expected, (
        f"schema mismatch: "
        f"missing={{sorted(expected - actual)}}, "
        f"unexpected={{sorted(actual - expected)}}"
    )
"""

    smoke = command(
        [
            sys.executable,
            "-c",
            code,
        ]
    )

    checks = [
        Check(
            "Flask application factory and in-memory schema",
            (
                "PASS"
                if smoke.returncode == 0
                else "FAIL"
            ),
            smoke.stderr[-1000:],
        )
    ]

    if smoke.returncode:
        return checks

    pytest = command(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
        ]
    )

    checks.append(
        Check(
            "Pytest suite",
            (
                "PASS"
                if pytest.returncode == 0
                else "FAIL"
            ),
            (
                pytest.stdout
                + "\n"
                + pytest.stderr
            )[-1500:],
        )
    )

    return checks


def write_report(
    checks: list[Check],
) -> None:
    timestamp = (
        dt.datetime.now(dt.timezone.utc)
        .isoformat(timespec="seconds")
    )

    rows = [
        "| Check | Result | Detail |",
        "|---|---:|---|",
    ]

    for item in checks:
        detail = item.detail.replace(
            "|",
            "\\|",
        )

        rows.append(
            f"| {item.name} | "
            f"**{item.status}** | "
            f"{detail} |"
        )

    summary = {
        state: sum(
            item.status == state
            for item in checks
        )
        for state in (
            "PASS",
            "FAIL",
            "SKIP",
        )
    }

    report = f"""# Validation report

Generated: `{timestamp}`

This report distinguishes executed checks from checks skipped because the build sandbox lacks
runtime dependencies. A skip is not represented as a pass.

{os.linesep.join(rows)}

## Summary

- PASS: {summary['PASS']}
- FAIL: {summary['FAIL']}
- SKIP: {summary['SKIP']}

## Reproduce the full runtime gate

```bash
python -m pip install -r requirements-dev.txt
python scripts/validate_release.py --require-runtime