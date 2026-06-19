"""The MyQ Garage integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import MyQGarageClient
from .const import DOMAIN, get_scan_interval_seconds
from .coordinator import MyQGarageDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.COVER]


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options updates."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.update_interval = timedelta(seconds=get_scan_interval_seconds(entry))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MyQ Garage from a config entry."""
    session = async_get_clientsession(hass)
    client = MyQGarageClient(
        url=entry.data[CONF_URL],
        api_key=entry.data[CONF_API_KEY],
        session=session,
    )

    coordinator = MyQGarageDataUpdateCoordinator(
        hass,
        client=client,
        update_interval=timedelta(seconds=get_scan_interval_seconds(entry)),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
