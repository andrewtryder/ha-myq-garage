"""DataUpdateCoordinator for MyQ Garage."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import MyQGarageAuthError, MyQGarageClient, MyQGarageClientError
from .const import DOMAIN
from .models import MyQGarageDevice, parse_devices

_LOGGER = logging.getLogger(__name__)

type MyQGarageConfigEntry = ConfigEntry[MyQGarageDataUpdateCoordinator]


class MyQGarageDataUpdateCoordinator(DataUpdateCoordinator[dict[str, MyQGarageDevice]]):
    """Class to manage fetching MyQ Garage data."""

    config_entry: MyQGarageConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: MyQGarageConfigEntry,
        client: MyQGarageClient,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, MyQGarageDevice]:
        """Update data via library."""
        try:
            raw_devices = await self.client.get_devices()
        except MyQGarageAuthError as exception:
            raise ConfigEntryAuthFailed(
                f"Authentication failed: {exception}"
            ) from exception
        except MyQGarageClientError as exception:
            raise UpdateFailed(
                f"Error communicating with API: {exception}"
            ) from exception

        try:
            return parse_devices(raw_devices)
        except MyQGarageClientError as exception:
            raise UpdateFailed(f"Invalid API response: {exception}") from exception
