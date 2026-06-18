"""Tests for the MyQ Garage config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
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


async def test_config_flow_user_step(hass: HomeAssistant) -> None:
    """Test the user step shows the configuration form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_config_flow_success(hass: HomeAssistant) -> None:
    """Test a successful config flow creates an entry with a unique ID."""
    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        return_value=MOCK_DEVICE_DATA,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://myq-api.example.com/",
                CONF_API_KEY: "test_api_key",
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "MyQ Garage"
    assert result["data"] == {
        CONF_URL: "https://myq-api.example.com/",
        CONF_API_KEY: "test_api_key",
    }
    assert result["result"].unique_id == "https://myq-api.example.com"


async def test_config_flow_duplicate_url_aborts(hass: HomeAssistant) -> None:
    """Test configuring the same API URL twice is rejected."""
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="https://myq-api.example.com",
        data={
            CONF_URL: "https://myq-api.example.com",
            CONF_API_KEY: "existing_key",
        },
    )
    existing_entry.add_to_hass(hass)

    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        return_value=MOCK_DEVICE_DATA,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://myq-api.example.com/",
                CONF_API_KEY: "new_api_key",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_config_flow_connection_error(hass: HomeAssistant) -> None:
    """Test connection errors are surfaced to the user."""
    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        side_effect=MyQGarageConnectionError("Connection failed"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "test_api_key",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_config_flow_auth_error(hass: HomeAssistant) -> None:
    """Test authentication errors are surfaced to the user."""
    with patch(
        "custom_components.myq_garage.config_flow.MyQGarageClient.get_devices",
        side_effect=MyQGarageAuthError("Invalid API Key"),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                CONF_URL: "https://myq-api.example.com",
                CONF_API_KEY: "bad_api_key",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
