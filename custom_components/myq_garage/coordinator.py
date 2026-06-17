"""DataUpdateCoordinator for MyQ Garage."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import MyQGarageClient, MyQGarageClientError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MyQGarageDataUpdateCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Class to manage fetching MyQ Garage data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MyQGarageClient,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Update data via library."""
        try:
            return await self.client.get_devices()
        except MyQGarageClientError as exception:
            raise UpdateFailed(
                f"Error communicating with API: {exception}"
            ) from exception
