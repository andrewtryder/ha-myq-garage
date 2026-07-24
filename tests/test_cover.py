"""Tests for the MyQ Garage cover platform."""

from types import SimpleNamespace
from unittest.mock import patch

from homeassistant.components.cover import CoverDeviceClass
from homeassistant.const import (
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myq_garage.const import DOMAIN
from custom_components.myq_garage.cover import MyQGarageCover
from custom_components.myq_garage.models import MyQGarageDevice, MyQGarageDoorStatus

MOCK_DEVICE_DATA = [
    {
        "id": "door_1",
        "name": "Main Garage Door",
        "status": "closed",
    },
    {
        "id": "door_2",
        "name": "Side Garage Door",
        "status": "open",
    },
]


async def test_cover_entities(hass: HomeAssistant) -> None:
    """Test cover entity creation and state."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "url": "http://localhost:8080",
            "api_key": "test_api_key",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        return_value=MOCK_DEVICE_DATA,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Check the closed door
        state = hass.states.get("cover.main_garage_door_door")
        assert state
        assert state.state == STATE_CLOSED
        assert state.attributes.get("device_class") == CoverDeviceClass.GARAGE

        # Check the open door
        state2 = hass.states.get("cover.side_garage_door_door")
        assert state2
        assert state2.state == STATE_OPEN


async def test_cover_unavailable_when_device_missing(hass: HomeAssistant) -> None:
    """Test a cover becomes unavailable if its device disappears from the API."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "url": "http://localhost:8080",
            "api_key": "test_api_key",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        return_value=MOCK_DEVICE_DATA,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        coordinator = entry.runtime_data

    # The API stops returning door_2, e.g. it was removed from the account.
    remaining_device = [MOCK_DEVICE_DATA[0]]
    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        return_value=remaining_device,
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    state = hass.states.get("cover.main_garage_door_door")
    assert state
    assert state.state == STATE_CLOSED

    missing_state = hass.states.get("cover.side_garage_door_door")
    assert missing_state
    assert missing_state.state == STATE_UNAVAILABLE


def test_is_closed_returns_none_when_device_missing() -> None:
    """Test is_closed is defensive even if called while the device is gone."""
    device = MyQGarageDevice(
        id="door_1", name="Main Garage Door", status=MyQGarageDoorStatus.CLOSED
    )
    coordinator = SimpleNamespace(data={}, last_update_success=True)

    cover = MyQGarageCover(coordinator, device)

    assert cover.is_closed is None


async def test_cover_opening_and_closing_states(hass: HomeAssistant) -> None:
    """Test opening and closing statuses map to the matching cover states."""
    transitional_devices = [
        {"id": "door_1", "name": "Main Garage Door", "status": "opening"},
        {"id": "door_2", "name": "Side Garage Door", "status": "closing"},
    ]
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "url": "http://localhost:8080",
            "api_key": "test_api_key",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        return_value=transitional_devices,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("cover.main_garage_door_door")
        assert state
        assert state.state == STATE_OPENING

        state2 = hass.states.get("cover.side_garage_door_door")
        assert state2
        assert state2.state == STATE_CLOSING


def test_is_opening_and_is_closing_defensive_when_device_missing() -> None:
    """Test is_opening/is_closing are defensive if the device is gone."""
    device = MyQGarageDevice(
        id="door_1", name="Main Garage Door", status=MyQGarageDoorStatus.OPENING
    )
    coordinator = SimpleNamespace(data={}, last_update_success=True)

    cover = MyQGarageCover(coordinator, device)

    assert cover.is_opening is False
    assert cover.is_closing is False


def test_is_opening_and_is_closing_match_device_status() -> None:
    """Test is_opening/is_closing reflect the current device status."""
    opening_device = MyQGarageDevice(
        id="door_1", name="Main Garage Door", status=MyQGarageDoorStatus.OPENING
    )
    closing_device = MyQGarageDevice(
        id="door_2", name="Side Garage Door", status=MyQGarageDoorStatus.CLOSING
    )
    coordinator = SimpleNamespace(
        data={"door_1": opening_device, "door_2": closing_device},
        last_update_success=True,
    )

    opening_cover = MyQGarageCover(coordinator, opening_device)
    closing_cover = MyQGarageCover(coordinator, closing_device)

    assert opening_cover.is_opening is True
    assert opening_cover.is_closing is False
    assert closing_cover.is_closing is True
    assert closing_cover.is_opening is False
