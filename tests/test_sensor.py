"""Tests for the Generac PWRview sensor platform."""

from __future__ import annotations

import pytest

from homeassistant.components.generac_pwrview.const import DOMAIN, WATT_SECONDS_TO_KWH
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from tests.common import MockConfigEntry

from .conftest import MOCK_SERIAL


@pytest.mark.usefixtures("init_local_integration")
async def test_local_power_sensors(hass: HomeAssistant) -> None:
    """Test power sensor values from local mode."""
    state = hass.states.get("sensor.home_home_consumption_power")
    assert state is not None
    assert state.state == "1500"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfPower.WATT
    assert state.attributes[ATTR_DEVICE_CLASS] == "power"

    state = hass.states.get("sensor.home_solar_production_power")
    assert state is not None
    assert state.state == "3000"

    state = hass.states.get("sensor.home_grid_power")
    assert state is not None
    assert state.state == "-1500"


@pytest.mark.usefixtures("init_local_integration")
async def test_local_energy_sensors(hass: HomeAssistant) -> None:
    """Test energy sensor values from local mode."""
    state = hass.states.get("sensor.home_home_consumption_energy")
    assert state is not None
    assert float(state.state) == pytest.approx(5400000000 / WATT_SECONDS_TO_KWH)
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfEnergy.KILO_WATT_HOUR
    assert state.attributes[ATTR_DEVICE_CLASS] == "energy"

    state = hass.states.get("sensor.home_grid_import_energy")
    assert state is not None
    assert float(state.state) == pytest.approx(1800000000 / WATT_SECONDS_TO_KWH)

    state = hass.states.get("sensor.home_grid_export_energy")
    assert state is not None
    assert float(state.state) == pytest.approx(3600000000 / WATT_SECONDS_TO_KWH)


@pytest.mark.usefixtures("init_local_integration")
async def test_phase_sensors_disabled_by_default(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test that phase sensors are disabled by default."""
    entry = entity_registry.async_get("sensor.home_phase_a_voltage")
    assert entry is not None
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION

    entry = entity_registry.async_get("sensor.home_phase_b_voltage")
    assert entry is not None
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "init_local_integration")
async def test_phase_sensors_when_enabled(hass: HomeAssistant) -> None:
    """Test phase sensor values when enabled."""
    state = hass.states.get("sensor.home_phase_a_voltage")
    assert state is not None
    assert float(state.state) == pytest.approx(121.5)
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfElectricPotential.VOLT

    state = hass.states.get("sensor.home_phase_a_power")
    assert state is not None
    assert state.state == "800"

    state = hass.states.get("sensor.home_phase_b_voltage")
    assert state is not None
    assert float(state.state) == pytest.approx(121.3)

    state = hass.states.get("sensor.home_phase_b_power")
    assert state is not None
    assert state.state == "700"


@pytest.mark.usefixtures("init_local_integration")
async def test_device_registry(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_config_entry_local: MockConfigEntry,
) -> None:
    """Test device is registered correctly."""
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, MOCK_SERIAL)}
    )
    assert device is not None
    assert device.manufacturer == "Generac"
    assert device.model == "PWRview Energy Monitor"
    assert device.serial_number == MOCK_SERIAL


@pytest.mark.usefixtures("init_local_integration")
async def test_all_entities_assigned_to_device(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    mock_config_entry_local: MockConfigEntry,
) -> None:
    """Test that all entities are assigned to the device."""
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, MOCK_SERIAL)}
    )
    assert device is not None

    entity_entries = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry_local.entry_id
    )
    assert len(entity_entries) > 0

    for entity_entry in entity_entries:
        assert entity_entry.device_id == device.id


@pytest.mark.usefixtures("init_local_integration")
async def test_sensor_unique_ids(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_config_entry_local: MockConfigEntry,
) -> None:
    """Test that sensors have correct unique IDs."""
    entry = entity_registry.async_get("sensor.home_grid_power")
    assert entry is not None
    assert entry.unique_id == f"{MOCK_SERIAL}_grid_power"

    entry = entity_registry.async_get("sensor.home_home_consumption_energy")
    assert entry is not None
    assert entry.unique_id == f"{MOCK_SERIAL}_home_consumption_energy"
