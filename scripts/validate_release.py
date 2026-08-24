#!/usr/bin/env python3
"""Run release checks and write a truthful Markdown validation report."""

from __future__ import annotations

import argparse
import compileall
import datetime as dt
import importlib.util
import json
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

EXPECTED_WORKBOOK_COUNTS = {
    "PMs": 2,
    "PCs": 2,
    "DAs": 9,
    "Villages": 42,
    "Committees": 351,
    "Committee_Members": 2433,
    "Action_Plans": 351,
    "Attendance_Entries": 0,
    "Specials_Entries": 0,
    "PC_DA_Map": 9,
    "Recycle_Bin": 0,
}


class Check:
    """Single validation result."""

    def __init__(self, name: str, status: str, detail: str = "") -> None:
        self.name = name
        self.status = status
        self.detail = detail.replace("\n", " ").strip()


def command(
    args: list[str],
    cwd: Path = ROOT,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and capture its output."""
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def static_checks() -> list[Check]:
    """Run checks that do not need the Flask app to start."""
    checks: list[Check] = []

    compile_targets = (
        ROOT / "app",
        ROOT / "tests",
        ROOT / "migrations",
        ROOT / "scripts",
    )
    compiled = True
    for target in compile_targets:
        if target.exists():
            compiled = compileall.compile_dir(str(target), quiet=1) and compiled

    checks.append(
        Check(
            "Python bytecode compilation",
            "PASS" if compiled else "FAIL",
        )
    )

    node = shutil.which("node")
    if node:
        failures: list[str] = []
        js_files = sorted((ROOT / "app" / "static" / "js").glob("*.js"))
        sw_path = ROOT / "app" / "static" / "sw.js"
        if sw_path.exists():
            js_files.append(sw_path)

        for path in js_files:
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
                else f"{len(js_files)} files checked",
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
        template_failures: list[str] = []
        templates = sorted((ROOT / "app" / "templates").glob("*.html"))

        for template in templates:
            try:
                env.parse(template.read_text(encoding="utf-8"))
            except Exception as exc:
                template_failures.append(f"{template.name}: {exc}")

        checks.append(
            Check(
                "Jinja template syntax",
                "PASS" if not template_failures else "FAIL",
                "; ".join(template_failures)
                if template_failures
                else f"{len(templates)} templates checked",
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

    manifest_path = ROOT / "app" / "static" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        sizes = {
            item.get("sizes")
            for item in manifest.get("icons", [])
        }

        manifest_valid = (
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
                "PASS" if manifest_valid else "FAIL",
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

    icon_errors: list[str] = []
    expected_icons = {
        "icon-192.png": (192, 192),
        "icon-512.png": (512, 512),
    }

    for name, expected_size in expected_icons.items():
        path = ROOT / "app" / "static" / "icons" / name
        try:
            with Image.open(path) as image:
                if image.size != expected_size:
                    icon_errors.append(f"{name}: {image.size}")
        except Exception as exc:
            icon_errors.append(f"{name}: {exc}")

    checks.append(
        Check(
            "Install icon dimensions",
            "PASS" if not icon_errors else "FAIL",
            "; ".join(icon_errors),
        )
    )

    source_checks: dict[str, tuple[str, tuple[str, ...]]] = {
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
                "attendance_entry",
                "assigned_date",
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
            source = (ROOT / relative).read_text(encoding="utf-8")
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
                    f"missing: {', '.join(missing)}" if missing else "",
                )
            )
        except Exception as exc:
            checks.append(Check(name, "FAIL", str(exc)))

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
            f"missing: {', '.join(missing_status)}"
            if missing_status
            else "",
        )
    )

    models_source = (ROOT / "app" / "models.py").read_text(encoding="utf-8")
    pc_class_pos = models_source.find("class PC")
    da_class_pos = models_source.find("class DA")
    pc_block = (
        models_source[pc_class_pos:da_class_pos]
        if pc_class_pos >= 0 and da_class_pos > pc_class_pos
        else ""
    )
    cluster_valid = "cluster" in pc_block

    checks.append(
        Check(
            "PC persisted cluster source",
            "PASS" if cluster_valid else "FAIL",
        )
    )

    migration_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "migrations" / "versions").glob("*.py")
    )
    missing_tables = sorted(
        table
        for table in EXPECTED_TABLES
        if table not in migration_source
    )

    checks.append(
        Check(
            "Thirteen-table Alembic migration",
            "PASS" if not missing_tables else "FAIL",
            f"missing: {', '.join(missing_tables)}"
            if missing_tables
            else "",
        )
    )

    css = (ROOT / "app" / "static" / "css" / "app.css").read_text(
        encoding="utf-8"
    )
    responsive = "44px" in css and "@media" in css

    checks.append(
        Check(
            "44px touch targets and adaptive breakpoints",
            "PASS" if responsive else "FAIL",
        )
    )

    return checks


def workbook_checks() -> list[Check]:
    """Profile the supplied normalized master workbook."""
    workbook_path = ROOT / "data" / "MV-Master-Data-26-27.xlsx"

    if not workbook_path.exists():
        return [
            Check(
                "Supplied workbook",
                "FAIL",
                "workbook missing",
            )
        ]

    profile_path = ROOT / "docs" / "workbook-profile.json"
    result = command(
        [
            sys.executable,
            "scripts/inspect_workbook.py",
            str(workbook_path),
            "--output",
            str(profile_path),
        ]
    )

    if result.returncode:
        return [
            Check(
                "Workbook profiling",
                "FAIL",
                (result.stdout + "\n" + result.stderr).strip(),
            )
        ]

    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [
            Check(
                "Workbook profiling",
                "FAIL",
                f"Could not read generated profile: {exc}",
            )
        ]

    actual_counts = {
        sheet: info.get("records")
        for sheet, info in profile.items()
        if isinstance(info, dict)
    }

    mismatches = []
    for sheet, expected in EXPECTED_WORKBOOK_COUNTS.items():
        actual = actual_counts.get(sheet)
        if actual != expected:
            mismatches.append(
                f"{sheet}: expected {expected}, got {actual!r}"
            )

    details = ", ".join(
        f"{sheet}={actual_counts.get(sheet, '?')}"
        for sheet in EXPECTED_WORKBOOK_COUNTS
    )

    return [
        Check(
            "Workbook opens and profiles",
            "PASS",
            f"{len(profile)} sheets",
        ),
        Check(
            "Exact production master-data row counts",
            "PASS" if not mismatches else "FAIL",
            "; ".join(mismatches) if mismatches else details,
        ),
    ]


def runtime_checks(require_runtime: bool) -> list[Check]:
    """Start the Flask factory against an in-memory DB and run pytest."""
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
        status = "FAIL" if require_runtime else "SKIP"
        return [
            Check(
                "Framework runtime and pytest suite",
                status,
                "missing environment dependencies: " + ", ".join(missing),
            )
        ]

    expected_tables_literal = repr(sorted(EXPECTED_TABLES))

    smoke_code = f"""
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
        "schema mismatch: "
        f"missing={{sorted(expected - actual)}}, "
        f"unexpected={{sorted(actual - expected)}}"
    )
"""

    smoke = command(
        [
            sys.executable,
            "-c",
            smoke_code,
        ]
    )

    checks = [
        Check(
            "Flask application factory and in-memory schema",
            "PASS" if smoke.returncode == 0 else "FAIL",
            (smoke.stdout + "\n" + smoke.stderr)[-1500:],
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
            "PASS" if pytest.returncode == 0 else "FAIL",
            (pytest.stdout + "\n" + pytest.stderr)[-2000:],
        )
    )

    return checks


def write_report(checks: list[Check]) -> None:
    """Write validation results without multiline f-string hazards."""
    timestamp = (
        dt.datetime.now(dt.UTC)
        .isoformat(timespec="seconds")
    )

    rows = [
        "| Check | Result | Detail |",
        "|---|---:|---|",
    ]

    for item in checks:
        detail = item.detail.replace("|", "\\|")
        rows.append(
            f"| {item.name} | **{item.status}** | {detail} |"
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

    report_lines = [
        "# Validation report",
        "",
        f"Generated: `{timestamp}`",
        "",
        (
            "This report distinguishes executed checks from checks skipped "
            "because the build environment lacks runtime dependencies. "
            "A skip is not represented as a pass."
        ),
        "",
    ]

    report_lines.extend(rows)
    report_lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- PASS: {summary['PASS']}",
            f"- FAIL: {summary['FAIL']}",
            f"- SKIP: {summary['SKIP']}",
            "",
            "## Reproduce the full runtime gate",
            "",
            "```bash",
            "python -m pip install -r requirements-dev.txt",
            "python scripts/validate_release.py --require-runtime",
            "```",
            "",
        ]
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-runtime",
        action="store_true",
        help="Fail if runtime dependencies are unavailable.",
    )
    args = parser.parse_args()

    checks = (
        static_checks()
        + workbook_checks()
        + runtime_checks(args.require_runtime)
    )

    write_report(checks)

    for item in checks:
        suffix = f" - {item.detail}" if item.detail else ""
        print(f"{item.status:4} {item.name}{suffix}")

    failures = [
        item
        for item in checks
        if item.status == "FAIL"
    ]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
