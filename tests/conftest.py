"""Fixtures for Generac PWRview tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

from generac_pwrview import (
    LocalChannel,
    LocalSample,
    LiveSample,
    LocationInfo,
    SensorInfo,
    Stats,
    UserInfo,
)
import pytest

from homeassistant.components.generac_pwrview.const import (
    CONF_API_SECRET,
    CONF_SERIAL_NUMBER,
    DOMAIN,
    PWRviewMode,
)
from homeassistant.const import CONF_API_KEY, CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

MOCK_SERIAL = "MAH0000000001"
MOCK_SENSOR_ID = "0x0000000000000001"
MOCK_HOST = "192.168.1.100"
MOCK_LOCATION = "Home"
MOCK_API_KEY = "test-api-key"
MOCK_API_SECRET = "test-api-secret"


@pytest.fixture
def mock_config_entry_local() -> MockConfigEntry:
    """Return a mock config entry for local mode."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"PWRview {MOCK_SERIAL}",
        data={
            CONF_API_KEY: None,
            CONF_API_SECRET: None,
            "sensor_id": None,
            CONF_HOST: MOCK_HOST,
            "serial_number": MOCK_SERIAL,
            "location_name": MOCK_LOCATION,
            "mode": PWRviewMode.LOCAL,
        },
        unique_id=MOCK_SERIAL,
    )


@pytest.fixture
def mock_config_entry_cloud() -> MockConfigEntry:
    """Return a mock config entry for cloud mode."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=MOCK_LOCATION,
        data={
            CONF_API_KEY: MOCK_API_KEY,
            CONF_API_SECRET: MOCK_API_SECRET,
            "sensor_id": MOCK_SENSOR_ID,
            CONF_HOST: MOCK_HOST,
            "serial_number": MOCK_SERIAL,
            "location_name": MOCK_LOCATION,
            "mode": PWRviewMode.CLOUD,
        },
        unique_id=MOCK_SERIAL,
    )


def _make_local_sample() -> LocalSample:
    """Create a mock local sample with realistic data."""
    return LocalSample(
        timestamp=None,
        channels=[
            LocalChannel(
                channel_type="CONSUMPTION",
                power=1500,
                energy_imported=5400000000,
                energy_exported=0,
                voltage=121.5,
            ),
            LocalChannel(
                channel_type="GENERATION",
                power=3000,
                energy_imported=10800000000,
                energy_exported=0,
                voltage=121.3,
            ),
            LocalChannel(
                channel_type="NET",
                power=-1500,
                energy_imported=1800000000,
                energy_exported=3600000000,
                voltage=121.4,
            ),
            LocalChannel(
                channel_type="PHASE_A_CONSUMPTION",
                power=800,
                energy_imported=2880000000,
                energy_exported=0,
                voltage=121.5,
            ),
            LocalChannel(
                channel_type="PHASE_B_CONSUMPTION",
                power=700,
                energy_imported=2520000000,
                energy_exported=0,
                voltage=121.3,
            ),
        ],
    )


def _make_live_sample() -> LiveSample:
    """Create a mock cloud live sample."""
    return LiveSample(
        timestamp=None,
        consumption_power=1500,
        generation_power=3000,
        net_power=-1500,
        consumption_energy=5400000000,
        generation_energy=10800000000,
        net_energy=1800000000,
    )


def _make_user_info() -> UserInfo:
    """Create a mock user info response."""
    return UserInfo(
        locations=[
            LocationInfo(
                name=MOCK_LOCATION,
                sensors=[
                    SensorInfo(
                        sensor_id=MOCK_SENSOR_ID,
                        serial_number=MOCK_SERIAL,
                        ip_address=MOCK_HOST,
                    )
                ],
            )
        ]
    )


@pytest.fixture
def mock_local_client() -> Generator[AsyncMock]:
    """Return a mocked PWRviewLocalClient."""
    with patch(
        "homeassistant.components.generac_pwrview.coordinator.PWRviewLocalClient",
        autospec=True,
    ) as mock_cls:
        client = mock_cls.return_value
        client.get_current_sample = AsyncMock(return_value=_make_local_sample())
        yield client


@pytest.fixture
def mock_cloud_client() -> Generator[AsyncMock]:
    """Return a mocked PWRviewClient."""
    with patch(
        "homeassistant.components.generac_pwrview.coordinator.PWRviewClient",
        autospec=True,
    ) as mock_cls:
        client = mock_cls.return_value
        client.get_user_information = AsyncMock(return_value=_make_user_info())
        client.get_live_sample = AsyncMock(return_value=_make_live_sample())
        client.get_stats = AsyncMock(
            return_value=[
                Stats(
                    start=None,
                    end=None,
                    consumption_energy=5400000000,
                    generation_energy=10800000000,
                    imported_energy=1800000000,
                    exported_energy=3600000000,
                )
            ]
        )
        client.get_samples = AsyncMock(return_value=[])
        yield client


@pytest.fixture
def platforms() -> list[Platform]:
    """Return platforms to test."""
    return [Platform.SENSOR]


@pytest.fixture
async def init_local_integration(
    hass: HomeAssistant,
    mock_config_entry_local: MockConfigEntry,
    mock_local_client: AsyncMock,
    platforms: list[Platform],
) -> MockConfigEntry:
    """Set up the integration in local mode for testing."""
    mock_config_entry_local.add_to_hass(hass)

    with patch(
        "homeassistant.components.generac_pwrview.PLATFORMS", platforms
    ):
        await hass.config_entries.async_setup(mock_config_entry_local.entry_id)
        await hass.async_block_till_done()

    return mock_config_entry_local


@pytest.fixture
async def init_cloud_integration(
    hass: HomeAssistant,
    mock_config_entry_cloud: MockConfigEntry,
    mock_cloud_client: AsyncMock,
    platforms: list[Platform],
) -> MockConfigEntry:
    """Set up the integration in cloud mode for testing."""
    mock_config_entry_cloud.add_to_hass(hass)

    with patch(
        "homeassistant.components.generac_pwrview.PLATFORMS", platforms
    ):
        await hass.config_entries.async_setup(mock_config_entry_cloud.entry_id)
        await hass.async_block_till_done()

    return mock_config_entry_cloud
