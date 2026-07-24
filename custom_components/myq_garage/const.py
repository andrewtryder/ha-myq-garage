"""Constants for the MyQ Garage integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

DOMAIN = "myq_garage"

CONF_SCAN_INTERVAL_SECONDS = "scan_interval_seconds"
DEFAULT_SCAN_INTERVAL_SECONDS = 30
MIN_SCAN_INTERVAL_SECONDS = 10
MAX_SCAN_INTERVAL_SECONDS = 3600


def invalid_legacy_url_issue_id(entry_id: str) -> str:
    """Return the repair issue id for an invalid legacy config URL."""
    return f"invalid_legacy_url_{entry_id}"


def get_scan_interval_seconds(entry: ConfigEntry) -> int:
    """Return the configured scan interval in seconds."""
    return entry.options.get(CONF_SCAN_INTERVAL_SECONDS, DEFAULT_SCAN_INTERVAL_SECONDS)
