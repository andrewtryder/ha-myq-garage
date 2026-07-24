"""Diagnostics support for MyQ Garage."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .coordinator import MyQGarageConfigEntry

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MyQGarageConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry with secrets redacted."""
    coordinator = entry.runtime_data
    devices = {
        device_id: {
            "id": device.id,
            "name": device.name,
            "status": device.status.value,
        }
        for device_id, device in (coordinator.data or {}).items()
    }
    return {
        "entry": async_redact_data(
            {
                "title": entry.title,
                "domain": entry.domain,
                "version": entry.version,
                "unique_id": entry.unique_id,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            TO_REDACT,
        ),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
        },
        "devices": devices,
    }
