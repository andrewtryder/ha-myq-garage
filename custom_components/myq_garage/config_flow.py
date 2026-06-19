"""Config flow for MyQ Garage integration."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import MyQGarageAuthError, MyQGarageClient, MyQGarageConnectionError
from .const import (
    CONF_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
    get_scan_interval_seconds,
)

_LOGGER = logging.getLogger(__name__)


def _normalize_url(url: str) -> str:
    """Normalize the API URL for use as a unique config entry ID."""
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_API_KEY): str,
    }
)


def _options_schema(default_scan_interval: int) -> vol.Schema:
    """Return the options flow schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_SCAN_INTERVAL_SECONDS,
                default=default_scan_interval,
            ): vol.Coerce(int),
        }
    )


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    client = MyQGarageClient(data[CONF_URL], data[CONF_API_KEY], session)

    # Simple validation test
    await client.get_devices()

    return {"title": "MyQ Garage"}


class MyQGarageOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle MyQ Garage options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            scan_interval = user_input[CONF_SCAN_INTERVAL_SECONDS]
            if (
                scan_interval < MIN_SCAN_INTERVAL_SECONDS
                or scan_interval > MAX_SCAN_INTERVAL_SECONDS
            ):
                errors["base"] = "invalid_scan_interval"
            else:
                return self.async_create_entry(
                    title="",
                    data={CONF_SCAN_INTERVAL_SECONDS: scan_interval},
                )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(get_scan_interval_seconds(self.config_entry)),
            errors=errors,
        )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MyQ Garage."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return MyQGarageOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        await self.async_set_unique_id(_normalize_url(user_input[CONF_URL]))
        self._abort_if_unique_id_configured()

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except MyQGarageConnectionError:
            errors["base"] = "cannot_connect"
        except MyQGarageAuthError:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
