"""Tests for MyQ Garage integration lifecycle setup and unload."""

from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myq_garage.client import (
    MyQGarageAuthError,
    MyQGarageClientError,
    MyQGarageConnectionError,
)
from custom_components.myq_garage.const import DOMAIN

MOCK_DEVICE_DATA = [
    {
        "id": "door_1",
        "name": "Main Garage Door",
        "status": "closed",
    }
]


async def test_setup_unload_entry(hass: HomeAssistant) -> None:
    """Test setting up and unloading the config entry."""
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

        # Check if the entry is loaded successfully
        assert entry.state is ConfigEntryState.LOADED
        assert DOMAIN in hass.data
        assert entry.entry_id in hass.data[DOMAIN]

        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.data == MOCK_DEVICE_DATA

        # Test unloading
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.NOT_LOADED
        assert entry.entry_id not in hass.data[DOMAIN]


@pytest.mark.parametrize(
    ("exception", "error_message"),
    [
        (MyQGarageConnectionError("Connection failed"), "Error communicating with API"),
        (MyQGarageAuthError("Auth failed"), "Error communicating with API"),
        (MyQGarageClientError("Unknown API error"), "Error communicating with API"),
    ],
)
async def test_setup_entry_failures(
    hass: HomeAssistant, exception: Exception, error_message: str
) -> None:
    """Test setup errors inside coordinator update."""
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
        side_effect=exception,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.SETUP_RETRY
