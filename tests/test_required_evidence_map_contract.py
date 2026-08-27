from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.entries import EntryValidationError, _coordinates

ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_device_location_is_required_even_when_village_has_coordinates():
    village = SimpleNamespace(latitude=17.4, longitude=78.5)

    with pytest.raises(EntryValidationError, match="device location is required"):
        _coordinates({}, village)


def test_valid_device_location_is_preserved():
    village = SimpleNamespace(latitude=None, longitude=None)

    assert _coordinates(
        {"latitude": "17.385044", "longitude": "78.486671"},
        village,
    ) == (17.385044, 78.486671, "device")


def test_null_island_is_rejected():
    village = SimpleNamespace(latitude=None, longitude=None)

    with pytest.raises(EntryValidationError, match="invalid"):
        _coordinates({"latitude": "0", "longitude": "0"}, village)


def test_photo_and_location_are_required_in_field_ui_and_server():
    template = read("app/templates/field.html")
    field_js = read("app/static/js/field.js")
    entries = read("app/services/entries.py")

    assert 'id="photo-input"' in template
    assert 'capture="environment" required' in template
    assert "A field evidence photo is required before submitting." in field_js
    assert "Current GPS location is required." in field_js
    assert "def _required_photo(" in entries
    assert 'raise EntryValidationError("A field evidence photo is required.")' in entries


def test_map_does_not_turn_null_coordinates_into_zero_zero():
    map_js = read("app/static/js/map.js")
    monitoring = read("app/services/monitoring.py")

    assert "value === null" in map_js
    assert "value === undefined" in map_js
    assert "Math.abs(lat) < 0.000001" in map_js
    assert "map.setView(bounds[0], 13)" in map_js
    assert "selectinload(Village.specials_entries)" in monitoring
    assert '"location_source": location_source' in monitoring
    assert '"field-evidence"' in monitoring
