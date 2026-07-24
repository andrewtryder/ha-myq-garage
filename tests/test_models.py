"""Tests for MyQ Garage device payload validation."""

import pytest

from custom_components.myq_garage.models import (
    MyQGarageDataError,
    MyQGarageDoorStatus,
    extract_stable_id,
    parse_devices,
)


def test_extract_stable_id_valid() -> None:
    """Test a well-formed /info payload yields its installation id."""
    assert (
        extract_stable_id({"installation_id": "installation-123"}) == "installation-123"
    )


def test_extract_stable_id_strips_whitespace() -> None:
    """Test surrounding whitespace is stripped from the stable id."""
    assert (
        extract_stable_id({"installation_id": "  installation-123  "})
        == "installation-123"
    )


@pytest.mark.parametrize(
    "info",
    [
        None,
        [],
        "installation-123",
        {},
        {"installation_id": ""},
        {"installation_id": "   "},
        {"installation_id": 123},
        {"other_key": "installation-123"},
    ],
)
def test_extract_stable_id_invalid(info) -> None:
    """Test malformed or missing /info payloads yield None."""
    assert extract_stable_id(info) is None


def test_parse_devices_valid() -> None:
    """Test valid records are parsed into devices keyed by id."""
    devices = parse_devices(
        [
            {"id": "door_1", "name": "Main Garage Door", "status": "closed"},
            {"id": "door_2", "name": "Side Garage Door", "status": "open"},
        ]
    )

    assert set(devices) == {"door_1", "door_2"}
    assert devices["door_1"].status is MyQGarageDoorStatus.CLOSED
    assert devices["door_1"].is_closed is True
    assert devices["door_2"].is_closed is False


def test_parse_devices_missing_id_is_skipped() -> None:
    """Test records with no id are logged and skipped, not defaulted."""
    devices = parse_devices(
        [
            {"name": "No ID Door", "status": "closed"},
            {"id": "", "name": "Empty ID Door", "status": "closed"},
            {"id": "door_1", "name": "Main Garage Door", "status": "closed"},
        ]
    )

    assert set(devices) == {"door_1"}


def test_parse_devices_strips_id_whitespace() -> None:
    """Test surrounding whitespace on an id is stripped, not rejected."""
    devices = parse_devices(
        [{"id": "  door_1  ", "name": "Main Garage Door", "status": "closed"}]
    )

    assert set(devices) == {"door_1"}
    assert devices["door_1"].id == "door_1"


def test_parse_devices_duplicate_id_rejects_update() -> None:
    """Test a duplicate device id raises rather than silently merging."""
    with pytest.raises(MyQGarageDataError):
        parse_devices(
            [
                {"id": "door_1", "name": "Main Garage Door", "status": "closed"},
                {"id": "door_1", "name": "Duplicate Door", "status": "open"},
            ]
        )


def test_parse_devices_unknown_status_defaults_safely() -> None:
    """Test an unrecognized status is logged and treated as unknown."""
    devices = parse_devices(
        [{"id": "door_1", "name": "Main Garage Door", "status": "melting"}]
    )

    assert devices["door_1"].status is MyQGarageDoorStatus.UNKNOWN
    assert devices["door_1"].is_closed is None


def test_parse_devices_missing_name_uses_fallback() -> None:
    """Test a missing name falls back to a generic label, not the id."""
    devices = parse_devices([{"id": "door_1", "status": "closed"}])

    assert devices["door_1"].name == "MyQ Garage Door"


def test_parse_devices_empty_list() -> None:
    """Test an empty device list parses to an empty mapping."""
    assert parse_devices([]) == {}


def test_parse_devices_rejects_non_list_payload() -> None:
    """Test an unexpected top-level shape (e.g. a dict) is rejected."""
    with pytest.raises(MyQGarageDataError):
        parse_devices({"id": "door_1", "name": "Main Garage Door"})


def test_parse_devices_skips_non_object_records() -> None:
    """Test non-object entries in the list are logged and skipped."""
    devices = parse_devices(
        ["not-a-device", {"id": "door_1", "name": "Main Garage Door", "status": "open"}]
    )

    assert set(devices) == {"door_1"}
