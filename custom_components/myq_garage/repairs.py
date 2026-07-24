"""Repair flows for MyQ Garage."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .client import (
    MyQGarageAccountVerificationError,
    MyQGarageAuthError,
    MyQGarageConnectionError,
)
from .config_flow import ConfigFlow, _user_data_schema, validate_input
from .const import DOMAIN, invalid_legacy_url_issue_id
from .util import InsecureURLError, InvalidURLError, normalize_url

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


def _find_duplicate_url_entry(
    hass: HomeAssistant,
    normalized_url: str,
    *,
    exclude_entry_id: str,
) -> config_entries.ConfigEntry | None:
    """Return another entry already configured with the same normalized URL."""
    for other in hass.config_entries.async_entries(DOMAIN):
        if other.entry_id == exclude_entry_id:
            continue
        try:
            if normalize_url(other.data[CONF_URL]) == normalized_url:
                return other
        except InvalidURLError:
            continue
    return None


def _find_duplicate_unique_id_entry(
    hass: HomeAssistant,
    unique_id: str,
    *,
    exclude_entry_id: str,
) -> config_entries.ConfigEntry | None:
    """Return another entry already using the given stable installation ID."""
    for other in hass.config_entries.async_entries(DOMAIN):
        if other.entry_id == exclude_entry_id:
            continue
        if other.unique_id == unique_id:
            return other
    return None


def _normalize_repair_url(raw_url: str, errors: dict[str, str]) -> str | None:
    """Normalize a repair URL or populate a form error."""
    try:
        return normalize_url(raw_url)
    except InsecureURLError:
        errors["base"] = "insecure_url"
    except InvalidURLError:
        errors["base"] = "invalid_url"
    return None


def _identity_conflict(
    entry: config_entries.ConfigEntry, stable_id: str | None
) -> str | None:
    """Return a form error key when the stable id does not match the entry."""
    if (
        entry.unique_id is not None
        and stable_id is not None
        and entry.unique_id != stable_id
    ):
        return "wrong_account"
    return None


class InvalidLegacyUrlRepairFlow(RepairsFlow):
    """Repair flow that fixes an invalid legacy API URL in place."""

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
        """Update a migration-failed entry with a valid version-3 URL."""
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

    async def _async_validate_repair_input(
        self,
        entry: config_entries.ConfigEntry,
        user_input: dict[str, Any],
        errors: dict[str, str],
    ) -> tuple[dict[str, str], str | None] | data_entry_flow.FlowResult | None:
        """Validate repair form input.

        Returns ``(validated_input, stable_id)`` on success, an abort result when
        a duplicate exists, or ``None`` when a form error was recorded.
        """
        normalized_url = _normalize_repair_url(user_input[CONF_URL], errors)
        if normalized_url is None:
            return None

        if (
            _find_duplicate_url_entry(
                self.hass, normalized_url, exclude_entry_id=entry.entry_id
            )
            is not None
        ):
            return self.async_abort(reason="already_configured")

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

        stable_id = info["stable_id"]
        if conflict := _identity_conflict(entry, stable_id):
            errors["base"] = conflict
            return None

        if (
            stable_id is not None
            and _find_duplicate_unique_id_entry(
                self.hass, stable_id, exclude_entry_id=entry.entry_id
            )
            is not None
        ):
            return self.async_abort(reason="already_configured")

        return validated_input, stable_id

    async def _async_recover_entry(
        self,
        entry: config_entries.ConfigEntry,
        validated_input: dict[str, str],
        stable_id: str | None,
        *,
        preserved_entry_id: str,
        preserved_title: str,
        preserved_options: dict[str, Any],
    ) -> data_entry_flow.FlowResult:
        """Update the entry in place and set it up after a migration error."""
        # Entries stuck in MIGRATION_ERROR are not recoverable via async_reload,
        # so after updating version/data we reset the entry to NOT_LOADED and
        # set it up again using the public async_setup API.
        update_kwargs: dict[str, Any] = {
            "data": validated_input,
            "version": ConfigFlow.VERSION,
        }
        if entry.unique_id is None and stable_id is not None:
            update_kwargs["unique_id"] = stable_id

        self.hass.config_entries.async_update_entry(entry, **update_kwargs)

        if entry.state is config_entries.ConfigEntryState.MIGRATION_ERROR:
            entry._async_set_state(  # noqa: SLF001
                self.hass,
                config_entries.ConfigEntryState.NOT_LOADED,
                None,
            )

        try:
            loaded = await self.hass.config_entries.async_setup(entry.entry_id)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception(
                "Repair updated entry %s but setup failed", entry.entry_id
            )
            return self.async_abort(reason="reload_failed")

        if not loaded or entry.state is not config_entries.ConfigEntryState.LOADED:
            _LOGGER.error(
                "Repair updated entry %s but it did not reach LOADED (state=%s)",
                entry.entry_id,
                entry.state,
            )
            return self.async_abort(reason="reload_failed")

        # Verify registry continuity invariants that async_update_entry preserves.
        assert entry.entry_id == preserved_entry_id
        assert entry.title == preserved_title
        assert dict(entry.options) == preserved_options

        ir.async_delete_issue(
            self.hass,
            DOMAIN,
            invalid_legacy_url_issue_id(entry.entry_id),
        )
        return self.async_create_entry(title="", data={})

    async def _async_apply_repair(
        self,
        entry: config_entries.ConfigEntry,
        user_input: dict[str, Any],
        errors: dict[str, str],
    ) -> data_entry_flow.FlowResult | None:
        """Validate repaired credentials and update the existing config entry."""
        preserved_title = entry.title
        preserved_options = dict(entry.options)
        preserved_entry_id = entry.entry_id

        validated = await self._async_validate_repair_input(entry, user_input, errors)
        if validated is None:
            return None
        if not isinstance(validated, tuple):
            return validated

        validated_input, stable_id = validated
        return await self._async_recover_entry(
            entry,
            validated_input,
            stable_id,
            preserved_entry_id=preserved_entry_id,
            preserved_title=preserved_title,
            preserved_options=preserved_options,
        )


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
