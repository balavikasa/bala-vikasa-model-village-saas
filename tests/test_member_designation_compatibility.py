"""Focused regression for the real DA attendance selector with legacy designations.

This harness loads the real _selected_members function without Flask so that it
can run in constrained CI/local environments. Full endpoint tests are separate.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

ENTRIES_PATH = Path(__file__).resolve().parents[1] / "app/services/entries.py"


class FakeField:
    def in_(self, values):
        return ("IN", tuple(values))

    def is_(self, value):
        return ("IS", value)

    def __eq__(self, value):
        return ("EQ", value)


class FakeMemberModel:
    id = FakeField()
    committee_id = FakeField()
    designation = FakeField()
    full_name = FakeField()
    is_enabled = FakeField()
    is_deleted = FakeField()


class FakeSelect:
    def where(self, *conditions):
        return self

    def order_by(self, *columns):
        return self


class FakeSession:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self, statement):
        return self.rows


class FakeDB:
    def __init__(self, rows):
        self.session = FakeSession(rows)

    def select(self, model):
        assert model is FakeMemberModel
        return FakeSelect()


def load_actual_selector(rows):
    tree = ast.parse(ENTRIES_PATH.read_text(encoding="utf-8"))
    actual = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                  and node.name == "_selected_members")
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), actual], type_ignores=[])
    code = compile(ast.fix_missing_locations(module), str(ENTRIES_PATH), "exec")

    class EntryValidationError(ValueError):
        pass

    namespace = {
        "db": FakeDB(rows), "CommitteeMember": FakeMemberModel,
        "EntryValidationError": EntryValidationError,
        "VISIT_DESIGNATIONS": {"President", "Vice President", "Secretary", "Member"},
        "_member_ids": lambda value: [int(v) for v in value],
    }
    exec(code, namespace)
    return namespace["_selected_members"], EntryValidationError


@pytest.mark.parametrize("designation", [r"S\M", "Secretory", "Wise President", "Mem", "member", "", None])
def test_valid_member_may_attend_with_nonstandard_legacy_designation(designation):
    row = SimpleNamespace(id=42, full_name="D.Mounika", designation=designation,
                          gender="Female", committee_id=7, is_enabled=True, is_deleted=False)
    selector, _ = load_actual_selector([row])
    selected = selector(SimpleNamespace(id=7), [42])
    assert selected == [row]
    assert selected[0].designation == designation  # never silently rewrite master data


def test_missing_or_inaccessible_member_still_rejected():
    selector, error_type = load_actual_selector([])
    with pytest.raises(error_type, match="do not belong"):
        selector(SimpleNamespace(id=7), [42])
