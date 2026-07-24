"""Base entity for the MyQ Garage integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MyQGarageDataUpdateCoordinator
from .models import MyQGarageDevice


class MyQGarageEntity(CoordinatorEntity[MyQGarageDataUpdateCoordinator]):
    """Defines a base MyQ Garage entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MyQGarageDataUpdateCoordinator,
        device: MyQGarageDevice,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device.id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id)},
            name=device.name,
            manufacturer="MyQ",
            model="Custom API Wrapper",
        )

    @property
    def device(self) -> MyQGarageDevice | None:
        """Return the current device data from the coordinator, if present."""
        return self.coordinator.data.get(self._device_id)

    @property
    def available(self) -> bool:
        """Return True if the coordinator succeeded and the device is present."""
        return super().available and self._device_id in self.coordinator.data
