"""Tests for the MyQ Garage options flow."""

from datetime import timedelta
from unittest.mock import patch

from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

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


async def test_options_flow_init_form(hass: HomeAssistant) -> None:
    """Test the options flow shows the scan interval form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "test_api_key",
        },
        options={CONF_SCAN_INTERVAL_SECONDS: 60},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_default_value(hass: HomeAssistant) -> None:
    """Test saving the default scan interval when unset."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "test_api_key",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SCAN_INTERVAL_SECONDS: DEFAULT_SCAN_INTERVAL_SECONDS},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_SCAN_INTERVAL_SECONDS: DEFAULT_SCAN_INTERVAL_SECONDS}


async def test_options_flow_success(hass: HomeAssistant) -> None:
    """Test saving a valid scan interval."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "test_api_key",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SCAN_INTERVAL_SECONDS: 45},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_SCAN_INTERVAL_SECONDS: 45}


async def test_options_flow_invalid_scan_interval(hass: HomeAssistant) -> None:
    """Test an out-of-range scan interval is rejected."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "test_api_key",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SCAN_INTERVAL_SECONDS: 5},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_scan_interval"}


async def test_options_update_changes_coordinator_interval(
    hass: HomeAssistant,
) -> None:
    """Test updating options changes the coordinator poll interval."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_URL: "http://localhost:8080",
            CONF_API_KEY: "test_api_key",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        return_value=MOCK_DEVICE_DATA,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][entry.entry_id]
        assert coordinator.update_interval == timedelta(
            seconds=DEFAULT_SCAN_INTERVAL_SECONDS
        )

        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {CONF_SCAN_INTERVAL_SECONDS: 120},
        )
        await hass.async_block_till_done()

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert coordinator.update_interval == timedelta(seconds=120)
