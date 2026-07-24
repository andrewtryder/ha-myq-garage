"""Tests for MyQ Garage integration lifecycle setup and unload."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myq_garage import async_migrate_entry
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


async def test_reauth_while_loaded_updates_in_place_without_reload(
    hass: HomeAssistant,
) -> None:
    """Test reauth on an already-loaded entry updates the client in place.

    When the coordinator hits an auth failure on a routine (non-first)
    refresh, HA starts a reauth flow while the entry stays loaded. Once
    reauth succeeds, the update listener should apply the new API key to
    the existing client/coordinator instead of the entry being reloaded.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "url": "http://localhost:8080",
            "api_key": "good_api_key",
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
    coordinator = entry.runtime_data

    # The API key is later revoked; a routine refresh fails authentication
    # and starts a reauth flow without unloading the entry.
    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        side_effect=MyQGarageAuthError("Invalid API Key"),
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

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
        patch(
            "custom_components.myq_garage.client.MyQGarageClient.get_devices",
            return_value=MOCK_DEVICE_DATA,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            reauth_flow["flow_id"],
            {"api_key": "new_good_api_key"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["api_key"] == "new_good_api_key"
    assert entry.state is ConfigEntryState.LOADED
    # The entry was updated in place by the update listener, not reloaded:
    # the coordinator/client instances are unchanged and already carry the
    # new key.
    assert entry.runtime_data is coordinator
    assert coordinator.client.api_key == "new_good_api_key"


async def test_migrate_entry_v1_clears_unique_id_and_normalizes_url(
    hass: HomeAssistant,
) -> None:
    """Test version 1 entries clear URL unique IDs and normalize stored URLs."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id="HTTPS://MyQ-API.Example.com:443/",
        data={
            "url": "HTTPS://MyQ-API.Example.com:443/",
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
    assert entry.version == 3
    assert entry.unique_id is None
    assert entry.data["url"] == "https://myq-api.example.com"


async def test_migrate_entry_v2_normalizes_url_preserves_unique_id(
    hass: HomeAssistant,
) -> None:
    """Test version 2 entries normalize URLs without clearing a stable unique ID."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="installation-123",
        data={
            "url": "http://LocalHost:8080/",
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
    assert entry.version == 3
    assert entry.unique_id == "installation-123"
    assert entry.data["url"] == "http://localhost:8080"


async def test_migrate_entry_invalid_legacy_url_fails(hass: HomeAssistant) -> None:
    """Test migration fails without mutating an entry that has an invalid URL."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="installation-123",
        data={
            "url": "https://myq-api.example.com/?token=secret",
            "api_key": "test_api_key",
        },
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.MIGRATION_ERROR
    assert entry.version == 2
    assert entry.unique_id == "installation-123"
    assert entry.data["url"] == "https://myq-api.example.com/?token=secret"
    assert entry.data["api_key"] == "test_api_key"


async def test_migrate_entry_v3_is_noop(hass: HomeAssistant) -> None:
    """Test already-migrated version 3 entries are left unchanged."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="installation-123",
        data={
            "url": "https://myq-api.example.com",
            "api_key": "test_api_key",
        },
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)
    assert entry.version == 3
    assert entry.unique_id == "installation-123"
    assert entry.data["url"] == "https://myq-api.example.com"


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


async def test_remove_config_entry_device_allows_absent_device(
    hass: HomeAssistant,
) -> None:
    """Users may delete devices that are no longer returned by the API."""
    from homeassistant.helpers import device_registry as dr

    from custom_components.myq_garage import async_remove_config_entry_device

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
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
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    present = device_registry.async_get_device(identifiers={(DOMAIN, "door_1")})
    assert present is not None
    assert not await async_remove_config_entry_device(hass, entry, present)

    # Simulate the API no longer returning the device.
    entry.runtime_data.data = {}
    assert await async_remove_config_entry_device(hass, entry, present)


async def test_remove_config_entry_device_when_unloaded(
    hass: HomeAssistant,
) -> None:
    """Unloaded entries allow device removal without runtime data."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers.device_registry import DeviceEntry

    from custom_components.myq_garage import async_remove_config_entry_device

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={
            "url": "http://localhost:8080",
            "api_key": "test_api_key",
        },
    )
    entry.add_to_hass(hass)

    device_entry = DeviceEntry(identifiers={(DOMAIN, "door_1")})
    assert await async_remove_config_entry_device(hass, entry, device_entry)
