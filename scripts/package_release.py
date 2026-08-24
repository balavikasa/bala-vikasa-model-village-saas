#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / f"{ROOT.name}.zip"
SOURCE_MANIFEST = ROOT / "SOURCE_MANIFEST.sha256"

TRANSIENT_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", "htmlcov"}
TRANSIENT_SUFFIXES = {".pyc", ".db", ".sqlite", ".sqlite3"}

for path in sorted(ROOT.rglob("*"), reverse=True):
    if path.is_dir() and path.name in TRANSIENT_DIRS:
        shutil.rmtree(path, ignore_errors=True)
for path in list(ROOT.rglob("*")):
    if path.is_file() and path.suffix in TRANSIENT_SUFFIXES:
        path.unlink()

entries = []
for path in sorted(ROOT.rglob("*")):
    if not path.is_file() or path == SOURCE_MANIFEST:
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    entries.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
SOURCE_MANIFEST.write_text("\n".join(entries) + "\n", encoding="utf-8")

if OUT.exists():
    OUT.unlink()
shutil.make_archive(str(OUT.with_suffix("")), "zip", ROOT.parent, ROOT.name)

archive_digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
OUT.with_suffix(OUT.suffix + ".sha256").write_text(
    f"{archive_digest}  {OUT.name}\n",
    encoding="utf-8",
)
print(OUT)
