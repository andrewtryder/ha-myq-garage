"""Repair flows for MyQ Garage."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant

from .client import (
    MyQGarageAccountVerificationError,
    MyQGarageAuthError,
    MyQGarageConnectionError,
)
from .config_flow import _user_data_schema, validate_input
from .const import DOMAIN
from .util import InvalidURLError, normalize_url

_LOGGER = logging.getLogger(__name__)


def _repair_error(exc: BaseException) -> str | None:
    """Map a validation exception to a repair-flow error key, if known."""
    if isinstance(exc, MyQGarageConnectionError):
        return "cannot_connect"
    if isinstance(exc, MyQGarageAuthError):
        return "invalid_auth"
    if isinstance(exc, MyQGarageAccountVerificationError):
        return "cannot_verify_account"
    return None


class InvalidLegacyUrlRepairFlow(RepairsFlow):
    """Repair flow that replaces an invalid legacy API URL."""

    def __init__(self, entry_id: str) -> None:
        """Initialize the repair flow for a specific config entry."""
        super().__init__()
        self._entry_id = entry_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of the repair flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> data_entry_flow.FlowResult:
        """Replace a migration-failed entry with a valid version-3 entry."""
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            return self.async_abort(reason="entry_missing")

        if user_input is not None:
            result = await self._async_apply_repair(entry, user_input, errors)
            if result is not None:
                return result

        defaults = {CONF_URL: entry.data.get(CONF_URL, "")}
        return self.async_show_form(
            step_id="confirm",
            data_schema=_user_data_schema(defaults),
            errors=errors,
        )

    async def _async_apply_repair(
        self,
        entry: config_entries.ConfigEntry,
        user_input: dict[str, Any],
        errors: dict[str, str],
    ) -> data_entry_flow.FlowResult | None:
        """Validate repaired credentials and recreate the config entry."""
        try:
            normalized_url = normalize_url(user_input[CONF_URL])
        except InvalidURLError:
            errors["base"] = "invalid_url"
            return None

        validated_input = {
            CONF_URL: normalized_url,
            CONF_API_KEY: user_input[CONF_API_KEY],
        }
        try:
            info = await validate_input(
                self.hass,
                validated_input,
                require_stable_id=entry.unique_id is not None,
            )
        except Exception as err:  # pylint: disable=broad-except
            if (error := _repair_error(err)) is not None:
                errors["base"] = error
            else:
                _LOGGER.exception("Unexpected exception during repair")
                errors["base"] = "unknown"
            return None

        if (
            entry.unique_id is not None
            and info["stable_id"] is not None
            and entry.unique_id != info["stable_id"]
        ):
            errors["base"] = "wrong_account"
            return None

        # Entries stuck in MIGRATION_ERROR cannot be reloaded. Remove the
        # broken entry and recreate it via the normal user config flow.
        await self.hass.config_entries.async_remove(entry.entry_id)
        create_result = await self.hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=validated_input,
        )
        if create_result["type"] is not data_entry_flow.FlowResultType.CREATE_ENTRY:
            _LOGGER.error(
                "Repair failed to recreate config entry: %s",
                create_result,
            )
            return self.async_abort(reason="recreate_failed")
        return self.async_create_entry(title="", data={})


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create a repair flow for the given issue."""
    entry_id: str | None = None
    raw_entry_id = data.get("entry_id") if data else None
    if isinstance(raw_entry_id, str):
        entry_id = raw_entry_id
    elif issue_id.startswith("invalid_legacy_url_"):
        entry_id = issue_id.removeprefix("invalid_legacy_url_")

    if entry_id is None:
        raise ValueError(f"Unknown repair issue_id: {issue_id}")

    return InvalidLegacyUrlRepairFlow(entry_id)
