"""Config flow for MyQ Garage integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .client import (
    MyQGarageAccountVerificationError,
    MyQGarageAuthError,
    MyQGarageClient,
    MyQGarageClientError,
    MyQGarageConnectionError,
)
from .const import (
    CONF_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
    get_scan_interval_seconds,
)
from .models import extract_stable_id
from .util import InvalidURLError, normalize_url

_LOGGER = logging.getLogger(__name__)


def _user_data_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    """Return the schema for the user (and reconfigure) step."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_URL, default=defaults.get(CONF_URL)): TextSelector(
                TextSelectorConfig(type=TextSelectorType.URL)
            ),
            vol.Required(CONF_API_KEY): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        }
    )


def _reauth_data_schema() -> vol.Schema:
    """Return the schema for the reauth confirmation step."""
    return vol.Schema(
        {
            vol.Required(CONF_API_KEY): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
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


async def validate_input(
    hass: HomeAssistant,
    data: dict[str, Any],
    *,
    require_stable_id: bool = False,
) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Also attempts to read a stable installation id from the optional
    ``/info`` endpoint, so a config entry can be identified by something
    more durable than its configured URL when the companion API supports
    it.

    When ``require_stable_id`` is False (user setup and unidentified
    legacy reauth), an unsupported or unreachable ``/info`` endpoint
    yields ``stable_id=None`` and callers fall back to other
    duplicate-entry detection.

    When ``require_stable_id`` is True (reauth for an already-identified
    entry), ``/info`` must return a usable installation id. Transport
    failures propagate as connection errors; a missing, malformed, or
    unsupported response raises ``MyQGarageAccountVerificationError``.
    """
    session = async_get_clientsession(hass)
    client = MyQGarageClient(data[CONF_URL], data[CONF_API_KEY], session)

    # Simple validation test
    await client.get_devices()

    stable_id: str | None = None
    try:
        info = await client.get_info()
    except MyQGarageClientError:
        if require_stable_id:
            raise
        _LOGGER.debug("Could not fetch optional /info endpoint", exc_info=True)
    else:
        stable_id = extract_stable_id(info)

    if require_stable_id and stable_id is None:
        raise MyQGarageAccountVerificationError(
            "Could not verify MyQ Garage installation identity via /info"
        )

    return {"title": "MyQ Garage", "stable_id": stable_id}


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

    # Version 2 stopped using the API URL as the config entry unique ID.
    # Version 3 normalizes stored API URLs for entries created before the
    # shared normalize_url helper. See async_migrate_entry in __init__.py.
    VERSION = 3

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return MyQGarageOptionsFlowHandler()

    def _find_duplicate_entry(
        self, normalized_url: str
    ) -> config_entries.ConfigEntry | None:
        """Return an existing entry configured with the same normalized URL."""
        for entry in self._async_current_entries(include_ignore=False):
            try:
                if normalize_url(entry.data[CONF_URL]) == normalized_url:
                    return entry
            except InvalidURLError:
                continue
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                normalized_url = normalize_url(user_input[CONF_URL])
            except InvalidURLError:
                errors["base"] = "invalid_url"
            else:
                if self._find_duplicate_entry(normalized_url) is not None:
                    return self.async_abort(reason="already_configured")

                # Validate against the normalized URL so the entry is created
                # (and the companion API queried) using the exact form that
                # will be stored and used for subsequent requests.
                validated_input = {**user_input, CONF_URL: normalized_url}
                try:
                    info = await validate_input(self.hass, validated_input)
                except MyQGarageConnectionError:
                    errors["base"] = "cannot_connect"
                except MyQGarageAuthError:
                    errors["base"] = "invalid_auth"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"
                else:
                    if info["stable_id"] is not None:
                        await self.async_set_unique_id(info["stable_id"])
                        self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=info["title"], data=validated_input
                    )

        return self.async_show_form(
            step_id="user", data_schema=_user_data_schema(user_input), errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Perform reauthentication upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Confirm reauthentication with a new API key."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            data = {**reauth_entry.data, CONF_API_KEY: user_input[CONF_API_KEY]}
            require_stable_id = reauth_entry.unique_id is not None
            try:
                info = await validate_input(
                    self.hass, data, require_stable_id=require_stable_id
                )
            except MyQGarageConnectionError:
                errors["base"] = "cannot_connect"
            except MyQGarageAuthError:
                errors["base"] = "invalid_auth"
            except MyQGarageAccountVerificationError:
                errors["base"] = "cannot_verify_account"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                stable_id = info["stable_id"]
                update_kwargs: dict[str, Any] = {
                    "data_updates": {CONF_API_KEY: user_input[CONF_API_KEY]}
                }
                if stable_id is not None:
                    await self.async_set_unique_id(stable_id)
                    # _abort_if_unique_id_mismatch treats a missing entry
                    # unique_id as a mismatch against the newly set flow id,
                    # so only use it when the entry already has an identity.
                    # When adopting an id for the first time, reject collisions
                    # with any other configured entry.
                    if reauth_entry.unique_id is not None:
                        self._abort_if_unique_id_mismatch(reason="wrong_account")
                    else:
                        self._abort_if_unique_id_configured()
                    update_kwargs["unique_id"] = stable_id

                # Use async_update_and_abort (not async_update_reload_and_abort):
                # this integration registers an update listener, and HA fires it
                # automatically once entry data changes below, letting it apply
                # the new credentials to the running coordinator in place.
                # Pairing a registered update listener with
                # async_update_reload_and_abort's own forced reload is
                # deprecated as of Core 2026.6 and becomes an error in 2026.12.
                result = self.async_update_and_abort(reauth_entry, **update_kwargs)

                # If the entry never finished loading (e.g. the original setup
                # failed authentication before the update listener was
                # registered), there is no listener to pick up this change, so
                # explicitly ask HA to (re)load the entry now.
                if reauth_entry.state is not config_entries.ConfigEntryState.LOADED:
                    self.hass.config_entries.async_schedule_reload(
                        reauth_entry.entry_id
                    )

                return result

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_reauth_data_schema(),
            errors=errors,
        )
