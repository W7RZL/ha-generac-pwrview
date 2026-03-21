"""Support for Generac PWRview sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import PWRviewChannel
from .coordinator import PWRviewConfigEntry, PWRviewCoordinator, PWRviewData
from .entity import PWRviewEntity

# Coordinator is used to centralize the data updates
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PWRviewSensorEntityDescription(SensorEntityDescription):
    """Describes PWRview sensor entity."""

    channel: PWRviewChannel
    value_fn: Callable[[PWRviewData, PWRviewChannel], StateType]
    exists_fn: Callable[[PWRviewData, PWRviewChannel], bool] = (
        lambda data, channel: channel in data.channels
    )


def _get_power(data: PWRviewData, channel: PWRviewChannel) -> StateType:
    """Get power value for a channel."""
    if channel not in data.channels:
        return None
    return data.channels[channel].power


def _get_energy_imported(data: PWRviewData, channel: PWRviewChannel) -> StateType:
    """Get imported energy value for a channel."""
    if channel not in data.channels:
        return None
    return data.channels[channel].energy_imported


def _get_energy_exported(data: PWRviewData, channel: PWRviewChannel) -> StateType:
    """Get exported energy value for a channel."""
    if channel not in data.channels:
        return None
    return data.channels[channel].energy_exported


def _get_voltage(data: PWRviewData, channel: PWRviewChannel) -> StateType:
    """Get voltage value for a channel."""
    if channel not in data.channels:
        return None
    return data.channels[channel].voltage


SENSORS: tuple[PWRviewSensorEntityDescription, ...] = (
    # Home consumption sensors
    PWRviewSensorEntityDescription(
        key="home_consumption_power",
        translation_key="home_consumption_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        channel=PWRviewChannel.CONSUMPTION,
        value_fn=_get_power,
    ),
    PWRviewSensorEntityDescription(
        key="home_consumption_energy",
        translation_key="home_consumption_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        channel=PWRviewChannel.CONSUMPTION,
        value_fn=_get_energy_imported,
    ),
    # Solar production sensors
    PWRviewSensorEntityDescription(
        key="solar_production_power",
        translation_key="solar_production_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        channel=PWRviewChannel.GENERATION,
        value_fn=_get_power,
    ),
    PWRviewSensorEntityDescription(
        key="solar_production_energy",
        translation_key="solar_production_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        channel=PWRviewChannel.GENERATION,
        value_fn=_get_energy_imported,
    ),
    # Grid sensors
    PWRviewSensorEntityDescription(
        key="grid_power",
        translation_key="grid_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        channel=PWRviewChannel.NET,
        value_fn=_get_power,
    ),
    PWRviewSensorEntityDescription(
        key="grid_import_energy",
        translation_key="grid_import_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        channel=PWRviewChannel.NET,
        value_fn=_get_energy_imported,
    ),
    PWRviewSensorEntityDescription(
        key="grid_export_energy",
        translation_key="grid_export_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        channel=PWRviewChannel.NET,
        value_fn=_get_energy_exported,
    ),
    # Phase A sensors (diagnostic)
    PWRviewSensorEntityDescription(
        key="phase_a_voltage",
        translation_key="phase_a_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        channel=PWRviewChannel.PHASE_A,
        value_fn=_get_voltage,
    ),
    PWRviewSensorEntityDescription(
        key="phase_a_power",
        translation_key="phase_a_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        channel=PWRviewChannel.PHASE_A,
        value_fn=_get_power,
    ),
    # Phase B sensors (diagnostic)
    PWRviewSensorEntityDescription(
        key="phase_b_voltage",
        translation_key="phase_b_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        channel=PWRviewChannel.PHASE_B,
        value_fn=_get_voltage,
    ),
    PWRviewSensorEntityDescription(
        key="phase_b_power",
        translation_key="phase_b_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        channel=PWRviewChannel.PHASE_B,
        value_fn=_get_power,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PWRviewConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up PWRview sensor based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        PWRviewSensorEntity(coordinator, description)
        for description in SENSORS
        if description.exists_fn(coordinator.data, description.channel)
    )


class PWRviewSensorEntity(PWRviewEntity, SensorEntity):
    """Defines a PWRview sensor entity."""

    entity_description: PWRviewSensorEntityDescription

    def __init__(
        self,
        coordinator: PWRviewCoordinator,
        description: PWRviewSensorEntityDescription,
    ) -> None:
        """Initialize a PWRview sensor entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial_number}_{description.key}"
        self._attr_translation_key = description.key

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(
            self.coordinator.data, self.entity_description.channel
        )
