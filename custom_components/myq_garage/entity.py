"""Base entity for the MyQ Garage integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MyQGarageDataUpdateCoordinator


class MyQGarageEntity(CoordinatorEntity[MyQGarageDataUpdateCoordinator]):
    """Defines a base MyQ Garage entity."""

    def __init__(
        self,
        coordinator: MyQGarageDataUpdateCoordinator,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.device_data = device_data
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this MyQ Garage device."""
        device_id = self.device_data.get("id", "unknown")
        device_name = self.device_data.get("name", "MyQ Garage Door")
        return DeviceInfo(
            identifiers={(DOMAIN, str(device_id))},
            name=device_name,
            manufacturer="MyQ",
            model="Custom API Wrapper",
        )
