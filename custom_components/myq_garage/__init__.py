"""The MyQ Garage integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.const import CONF_API_KEY, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import MyQGarageClient
from .const import DOMAIN, get_scan_interval_seconds, invalid_legacy_url_issue_id
from .coordinator import MyQGarageConfigEntry, MyQGarageDataUpdateCoordinator
from .util import InvalidURLError, normalize_url

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.COVER]


async def _async_update_listener(
    hass: HomeAssistant, entry: MyQGarageConfigEntry
) -> None:
    """Handle config entry data and options updates in place.

    This listener applies credential and polling-interval changes directly
    to the running coordinator/client instead of reloading the entry, since
    HA automatically schedules this listener whenever entry data or options
    change (see async_update_and_abort in config_flow.py).
    """
    coordinator = entry.runtime_data
    coordinator.client.url = entry.data[CONF_URL].rstrip("/")
    coordinator.client.api_key = entry.data[CONF_API_KEY]
    coordinator.update_interval = timedelta(seconds=get_scan_interval_seconds(entry))

    await coordinator.async_request_refresh()


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


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: MyQGarageConfigEntry,
    device_entry: dr.DeviceEntry,
) -> bool:
    """Allow removing devices that are no longer returned by the API.

    Devices still present in the latest successful coordinator data cannot be
    removed; once the API stops returning them they become unavailable and the
    user may delete them from the device registry.
    """
    if not hasattr(config_entry, "runtime_data") or config_entry.runtime_data is None:
        return True

    return not any(
        identifier[0] == DOMAIN and identifier[1] in config_entry.runtime_data.data
        for identifier in device_entry.identifiers
    )


async def async_migrate_entry(hass: HomeAssistant, entry: MyQGarageConfigEntry) -> bool:
    """Migrate an old config entry.

    Version 1 entries used the configured API URL as their unique ID, which
    Home Assistant's config-flow guidance identifies as an unstable,
    user-changeable source. Version 2 clears that unique ID; duplicate
    entries are instead prevented by comparing normalized URLs at config-flow
    time.

    Version 3 normalizes the stored API URL so entries created before the
    shared normalize_url helper receive the same canonical form as new
    entries (lowercase host, no default port, no trailing slash). Invalid
    legacy URLs fail migration without partially updating the entry.
    """
    if entry.version >= 3:
        return True

    new_data = dict(entry.data)
    new_unique_id = entry.unique_id

    if entry.version < 2:
        new_unique_id = None

    try:
        new_data[CONF_URL] = normalize_url(entry.data[CONF_URL])
    except InvalidURLError as err:
        _LOGGER.error(
            "Cannot migrate MyQ Garage config entry %s to version 3: %s (url=%r)",
            entry.entry_id,
            err,
            entry.data.get(CONF_URL),
        )
        ir.async_create_issue(
            hass,
            DOMAIN,
            invalid_legacy_url_issue_id(entry.entry_id),
            is_fixable=True,
            severity=ir.IssueSeverity.ERROR,
            translation_key="invalid_legacy_url",
            translation_placeholders={"url": str(entry.data.get(CONF_URL, ""))},
            data={"entry_id": entry.entry_id},
        )
        return False

    hass.config_entries.async_update_entry(
        entry,
        data=new_data,
        unique_id=new_unique_id,
        version=3,
    )
    ir.async_delete_issue(hass, DOMAIN, invalid_legacy_url_issue_id(entry.entry_id))
    return True
