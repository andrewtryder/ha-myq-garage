"""Cover platform for the MyQ Garage integration."""

from __future__ import annotations

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import MyQGarageConfigEntry, MyQGarageDataUpdateCoordinator
from .entity import MyQGarageEntity
from .models import MyQGarageDevice, MyQGarageDoorStatus

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MyQGarageConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MyQ Garage cover platform."""
    coordinator = entry.runtime_data
    known_ids: set[str] = set()

    @callback
    def _async_add_new_devices() -> None:
        """Add cover entities for devices observed since the last call."""
        new_devices = [
            device
            for device_id, device in coordinator.data.items()
            if device_id not in known_ids
        ]
        if not new_devices:
            return
        known_ids.update(device.id for device in new_devices)
        async_add_entities(
            MyQGarageCover(coordinator, device) for device in new_devices
        )

    _async_add_new_devices()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_devices))


class MyQGarageCover(MyQGarageEntity, CoverEntity):
    """Representation of a MyQ Garage cover."""

    _attr_device_class = CoverDeviceClass.GARAGE
    # Add open/close capabilities when the custom API supports them
    _attr_supported_features = CoverEntityFeature(0)
    _attr_translation_key = "door"

    def __init__(
        self,
        coordinator: MyQGarageDataUpdateCoordinator,
        device: MyQGarageDevice,
    ) -> None:
        """Initialize the cover."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.id}_cover"

    @property
    def is_closed(self) -> bool | None:
        """Return true if the cover is closed."""
        if (device := self.device) is None:
            return None
        return device.is_closed

    @property
    def is_opening(self) -> bool:
        """Return true if the cover is opening."""
        return (
            self.device is not None
            and self.device.status is MyQGarageDoorStatus.OPENING
        )

    @property
    def is_closing(self) -> bool:
        """Return true if the cover is closing."""
        return (
            self.device is not None
            and self.device.status is MyQGarageDoorStatus.CLOSING
        )
