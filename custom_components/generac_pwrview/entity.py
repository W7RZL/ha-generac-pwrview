"""Base entity for Generac PWRview."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PWRviewCoordinator


class PWRviewEntity(CoordinatorEntity[PWRviewCoordinator]):
    """Defines a base PWRview entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PWRviewCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.serial_number)},
            name=coordinator.location_name,
            manufacturer="Generac",
            model="PWRview Energy Monitor",
            serial_number=coordinator.serial_number,
        )
