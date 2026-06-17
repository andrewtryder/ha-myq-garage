"""Cover platform for the MyQ Garage integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MyQGarageDataUpdateCoordinator
from .entity import MyQGarageEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MyQ Garage cover platform."""
    coordinator: MyQGarageDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    # Assuming coordinator.data is a list of device dictionaries
    for device_data in coordinator.data:
        entities.append(MyQGarageCover(coordinator, device_data))

    async_add_entities(entities)


class MyQGarageCover(MyQGarageEntity, CoverEntity):
    """Representation of a MyQ Garage cover."""

    _attr_device_class = CoverDeviceClass.GARAGE
    # Add open/close capabilities when the custom API supports them
    _attr_supported_features = CoverEntityFeature(0)

    def __init__(
        self,
        coordinator: MyQGarageDataUpdateCoordinator,
        device_data: dict[str, Any],
    ) -> None:
        """Initialize the cover."""
        super().__init__(coordinator, device_data)
        self._attr_unique_id = f"{device_data.get('id', 'unknown')}_cover"
        self._attr_name = "Door"

    @property
    def is_closed(self) -> bool | None:
        """Return true if cover is closed."""
        # Find the device in the updated data
        for device in self.coordinator.data:
            if device.get("id") == self.device_data.get("id"):
                status = device.get("status")
                if status == "closed":
                    return True
                if status == "open":
                    return False
        return None
