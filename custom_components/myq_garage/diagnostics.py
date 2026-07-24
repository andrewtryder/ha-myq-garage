"""Diagnostics support for MyQ Garage."""

from __future__ import annotations

from typing import Any

from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .coordinator import MyQGarageConfigEntry

_REDACTED = "**REDACTED**"


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MyQGarageConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry with secrets redacted.

    Potentially identifying values (API key, URL, installation unique ID,
    device IDs, and device names) are replaced with deterministic
    placeholders within a single export. Operational fields such as door
    status, device count, poll interval, and coordinator health are kept.
    """
    coordinator = entry.runtime_data
    integration = await async_get_integration(hass, entry.domain)

    devices: dict[str, dict[str, str]] = {}
    for index, device in enumerate(
        sorted((coordinator.data or {}).values(), key=lambda d: d.id),
        start=1,
    ):
        devices[f"device_{index}"] = {
            "name": _REDACTED,
            "status": device.status.value,
        }

    return {
        "integration": {
            "version": integration.version,
            "domain": entry.domain,
        },
        "entry": {
            "version": entry.version,
            "has_unique_id": entry.unique_id is not None,
            "title_redacted": _REDACTED,
            "data": {
                CONF_API_KEY: _REDACTED,
                CONF_URL: _REDACTED,
            },
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
            "device_count": len(devices),
        },
        "devices": devices,
    }
