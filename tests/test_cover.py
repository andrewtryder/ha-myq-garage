"""Tests for the MyQ Garage cover platform."""

from unittest.mock import patch

from homeassistant.components.cover import CoverDeviceClass
from homeassistant.const import STATE_CLOSED, STATE_OPEN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myq_garage.const import DOMAIN

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
