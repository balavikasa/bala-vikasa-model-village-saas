
from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models import Committee, CommitteeMember, DA, PC, PM, Village
import app.services.workbook as workbook_service

WORKBOOK = Path(__file__).resolve().parents[1] / "data" / "MV-Master-Data-26-27.xlsx"


def _import_function():
    preferred = (
        "import_workbook",
        "load_workbook_data",
        "import_master_data",
    )
    for name in preferred:
        candidate = getattr(workbook_service, name, None)
        if callable(candidate):
            return candidate
    for name, candidate in inspect.getmembers(workbook_service, inspect.isfunction):
        if "import" in name and "workbook" in name:
            return candidate
    raise AssertionError("No public workbook import function was found")


@pytest.mark.integration
def test_supplied_workbook_imports_expected_master_counts(app):
    if not WORKBOOK.exists():
        pytest.skip("Supplied workbook is not present")
    importer = _import_function()
    with app.app_context():
        signature = inspect.signature(importer)
        kwargs = {}
        if "replace" in signature.parameters:
            kwargs["replace"] = False
        if "confirm" in signature.parameters:
            kwargs["confirm"] = False
        importer(WORKBOOK, **kwargs)
        expected = {
            PM: 2,
            PC: 2,
            DA: 9,
            Village: 42,
            Committee: 351,
            CommitteeMember: 2433,
        }
        for model, count in expected.items():
            actual = db.session.scalar(select(func.count()).select_from(model))
            assert actual == count, model.__name__
