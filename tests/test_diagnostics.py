"""Tests for MyQ Garage diagnostics."""

from unittest.mock import patch

from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myq_garage.const import DOMAIN
from custom_components.myq_garage.diagnostics import async_get_config_entry_diagnostics

MOCK_DEVICE_DATA = [
    {
        "id": "door_1",
        "name": "Main Garage Door",
        "status": "closed",
    }
]


async def test_config_entry_diagnostics_redacts_api_key(hass: HomeAssistant) -> None:
    """Diagnostics include device state and redact the API key."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id="installation-123",
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "super-secret-key",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.myq_garage.client.MyQGarageClient.get_devices",
        return_value=MOCK_DEVICE_DATA,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["data"][CONF_API_KEY] == "**REDACTED**"
    assert diagnostics["entry"]["data"][CONF_URL] == "https://myq-api.example.com"
    assert diagnostics["entry"]["unique_id"] == "installation-123"
    assert diagnostics["coordinator"]["last_update_success"] is True
    assert diagnostics["devices"]["door_1"]["status"] == "closed"
