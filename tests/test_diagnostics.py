"""Tests for MyQ Garage diagnostics privacy."""

import json
from unittest.mock import patch

from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myq_garage.const import CONF_SCAN_INTERVAL_SECONDS, DOMAIN
from custom_components.myq_garage.diagnostics import async_get_config_entry_diagnostics

API_KEY = "super-secret-key"
API_URL = "https://myq-api.example.com"
INSTALLATION_ID = "installation-123"
DEVICE_ID = "door_1"
DEVICE_NAME = "Main Garage Door"

MOCK_DEVICE_DATA = [
    {
        "id": DEVICE_ID,
        "name": DEVICE_NAME,
        "status": "closed",
    }
]


async def test_config_entry_diagnostics_redacts_sensitive_fields(
    hass: HomeAssistant,
) -> None:
    """Diagnostics keep operational data while redacting identifying fields."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id=INSTALLATION_ID,
        title="My Garage",
        data={
            CONF_URL: API_URL,
            CONF_API_KEY: API_KEY,
        },
        options={CONF_SCAN_INTERVAL_SECONDS: 45},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        return_value=MOCK_DEVICE_DATA,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    serialized = json.dumps(diagnostics)

    assert API_KEY not in serialized
    assert API_URL not in serialized
    assert "myq-api.example.com" not in serialized
    assert INSTALLATION_ID not in serialized
    assert DEVICE_ID not in serialized
    assert DEVICE_NAME not in serialized
    assert "My Garage" not in serialized

    assert diagnostics["entry"]["data"][CONF_API_KEY] == "**REDACTED**"
    assert diagnostics["entry"]["data"][CONF_URL] == "**REDACTED**"
    assert diagnostics["entry"]["has_unique_id"] is True
    assert diagnostics["entry"]["version"] == 3
    assert diagnostics["entry"]["options"][CONF_SCAN_INTERVAL_SECONDS] == 45
    assert diagnostics["coordinator"]["last_update_success"] is True
    assert diagnostics["coordinator"]["update_interval_seconds"] == 45
    assert diagnostics["coordinator"]["device_count"] == 1
    assert diagnostics["devices"]["device_1"]["status"] == "closed"
    assert diagnostics["devices"]["device_1"]["name"] == "**REDACTED**"
    assert diagnostics["integration"]["domain"] == DOMAIN
