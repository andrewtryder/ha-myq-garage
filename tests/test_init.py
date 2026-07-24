"""Tests for MyQ Garage integration lifecycle setup and unload."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myq_garage.client import (
    MyQGarageAuthError,
    MyQGarageClientError,
    MyQGarageConnectionError,
)
from custom_components.myq_garage.const import (
    CONF_SCAN_INTERVAL_SECONDS,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)

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

        coordinator = entry.runtime_data
        assert coordinator.data["door_1"].name == "Main Garage Door"
        assert coordinator.update_interval == timedelta(
            seconds=DEFAULT_SCAN_INTERVAL_SECONDS
        )

        # Test unloading
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    ("exception", "error_message"),
    [
        (MyQGarageConnectionError("Connection failed"), "Error communicating with API"),
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


async def test_setup_entry_auth_failure_triggers_reauth(hass: HomeAssistant) -> None:
    """Test that an auth failure during setup starts a reauth flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "url": "http://localhost:8080",
            "api_key": "bad_api_key",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        side_effect=MyQGarageAuthError("Invalid API Key"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR

    flows = hass.config_entries.flow.async_progress()
    reauth_flows = [flow for flow in flows if flow["context"]["source"] == "reauth"]
    assert len(reauth_flows) == 1
    assert reauth_flows[0]["context"]["entry_id"] == entry.entry_id


async def test_setup_custom_scan_interval(hass: HomeAssistant) -> None:
    """Test setup uses a custom scan interval from options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "url": "http://localhost:8080",
            "api_key": "test_api_key",
        },
        options={CONF_SCAN_INTERVAL_SECONDS: 60},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        return_value=MOCK_DEVICE_DATA,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        coordinator = entry.runtime_data
        assert coordinator.update_interval == timedelta(seconds=60)


async def test_migrate_entry_clears_url_unique_id(hass: HomeAssistant) -> None:
    """Test version 1 entries have their URL-based unique ID cleared."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id="http://localhost:8080",
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
    assert entry.version == 2
    assert entry.unique_id is None


async def test_reauth_flow_updates_api_key(hass: HomeAssistant) -> None:
    """Test a full reauth flow validates and stores the new API key."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "url": "http://localhost:8080",
            "api_key": "bad_api_key",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        side_effect=MyQGarageAuthError("Invalid API Key"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress()
    reauth_flow = next(flow for flow in flows if flow["context"]["source"] == "reauth")

    with (
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
        patch(
            "custom_components.myq_garage.config_flow.MyQGarageClient.get_info",
            return_value=None,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            reauth_flow["flow_id"],
            {"api_key": "good_api_key"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["api_key"] == "good_api_key"
    assert entry.state is ConfigEntryState.LOADED
