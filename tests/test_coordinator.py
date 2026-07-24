"""Tests for the MyQ Garage data update coordinator."""

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myq_garage.client import (
    MyQGarageAuthError,
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

DUPLICATE_DEVICE_DATA = [
    {"id": "door_1", "name": "Main Garage Door", "status": "closed"},
    {"id": "door_1", "name": "Duplicate Door", "status": "open"},
]


async def _setup_entry(hass: HomeAssistant) -> MockConfigEntry:
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

    assert entry.state is ConfigEntryState.LOADED
    return entry


async def test_duplicate_device_id_rejects_initial_setup(hass: HomeAssistant) -> None:
    """Test a duplicate device id in the API response fails initial setup."""
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
        return_value=DUPLICATE_DEVICE_DATA,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_duplicate_device_id_rejects_later_refresh(hass: HomeAssistant) -> None:
    """Test a duplicate device id on a later refresh does not corrupt data."""
    entry = await _setup_entry(hass)
    coordinator = entry.runtime_data

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        return_value=DUPLICATE_DEVICE_DATA,
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert coordinator.last_update_success is False
    # The last-known-good data is retained rather than being discarded.
    assert coordinator.data["door_1"].name == "Main Garage Door"


async def test_runtime_auth_failure_triggers_reauth(hass: HomeAssistant) -> None:
    """Test an auth failure on a later refresh starts a reauth flow."""
    entry = await _setup_entry(hass)
    coordinator = entry.runtime_data

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        side_effect=MyQGarageAuthError("Token revoked"),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert coordinator.last_update_success is False

    flows = hass.config_entries.flow.async_progress()
    reauth_flows = [flow for flow in flows if flow["context"]["source"] == "reauth"]
    assert len(reauth_flows) == 1
    assert reauth_flows[0]["context"]["entry_id"] == entry.entry_id


async def test_connection_failure_then_recovery(hass: HomeAssistant) -> None:
    """Test a transient connection failure followed by a successful refresh."""
    entry = await _setup_entry(hass)
    coordinator = entry.runtime_data

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        side_effect=MyQGarageConnectionError("Connection failed"),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert coordinator.last_update_success is False

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        return_value=MOCK_DEVICE_DATA,
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert coordinator.last_update_success is True
    assert coordinator.data["door_1"].name == "Main Garage Door"


async def test_empty_device_list(hass: HomeAssistant) -> None:
    """Test an empty device list loads successfully with no devices."""
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
        return_value=[],
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.data == {}
