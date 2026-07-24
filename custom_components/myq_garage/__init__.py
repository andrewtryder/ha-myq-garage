"""The MyQ Garage integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import CONF_API_KEY, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import MyQGarageClient
from .const import get_scan_interval_seconds
from .coordinator import MyQGarageConfigEntry, MyQGarageDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.COVER]


async def _async_update_listener(
    hass: HomeAssistant, entry: MyQGarageConfigEntry
) -> None:
    """Handle options updates."""
    entry.runtime_data.update_interval = timedelta(
        seconds=get_scan_interval_seconds(entry)
    )


async def async_setup_entry(hass: HomeAssistant, entry: MyQGarageConfigEntry) -> bool:
    """Set up MyQ Garage from a config entry."""
    session = async_get_clientsession(hass)
    client = MyQGarageClient(
        url=entry.data[CONF_URL],
        api_key=entry.data[CONF_API_KEY],
        session=session,
    )

    coordinator = MyQGarageDataUpdateCoordinator(
        hass,
        entry,
        client=client,
        update_interval=timedelta(seconds=get_scan_interval_seconds(entry)),
    )

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: MyQGarageConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: MyQGarageConfigEntry) -> bool:
    """Migrate an old config entry.

    Version 1 entries used the configured API URL as their unique ID, which
    Home Assistant's config-flow guidance identifies as an unstable,
    user-changeable source. Version 2 clears that unique ID; duplicate
    entries are instead prevented by comparing normalized URLs at config-flow
    time.
    """
    if entry.version == 1:
        hass.config_entries.async_update_entry(entry, unique_id=None, version=2)

    return True
