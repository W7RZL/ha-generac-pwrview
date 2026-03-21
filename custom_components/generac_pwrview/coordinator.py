"""DataUpdateCoordinator for Generac PWRview."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from generac_pwrview import (
    PWRviewClient,
    PWRviewConnectionError,
    PWRviewError,
    PWRviewLocalClient,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_API_SECRET,
    DOMAIN,
    LOGGER,
    SCAN_INTERVAL_CLOUD,
    SCAN_INTERVAL_LOCAL,
    WATT_SECONDS_TO_KWH,
    PWRviewChannel,
    PWRviewMode,
)

type PWRviewConfigEntry = ConfigEntry[PWRviewCoordinator]


@dataclass
class PWRviewChannelData:
    """Data for a single PWRview channel."""

    power: int | None = None
    energy_imported: float | None = None  # kWh
    energy_exported: float | None = None  # kWh
    voltage: float | None = None


@dataclass
class PWRviewData:
    """Data from PWRview sensor."""

    channels: dict[PWRviewChannel, PWRviewChannelData]
    timestamp: str | None = None

    @classmethod
    def empty(cls) -> PWRviewData:
        """Return empty data structure."""
        return cls(channels={})


class PWRviewCoordinator(DataUpdateCoordinator[PWRviewData]):
    """Coordinator to manage fetching PWRview data."""

    config_entry: PWRviewConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PWRviewConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.mode: PWRviewMode = PWRviewMode(entry.data.get("mode", PWRviewMode.CLOUD))
        self.sensor_id: str = entry.data["sensor_id"]
        self.host: str | None = entry.data.get(CONF_HOST)
        self.serial_number: str = entry.data["serial_number"]
        self.location_name: str = entry.data.get("location_name", "PWRview")

        session = async_get_clientsession(hass)

        # Set up clients based on mode
        self._cloud_client: PWRviewClient | None = None
        self._local_client: PWRviewLocalClient | None = None

        if self.mode == PWRviewMode.CLOUD:
            self._cloud_client = PWRviewClient(
                api_key=entry.data[CONF_API_KEY],
                api_secret=entry.data[CONF_API_SECRET],
                session=session,
            )
        elif self.host:
            self._local_client = PWRviewLocalClient(
                host=self.host,
                session=session,
            )

        # Determine update interval based on mode
        update_interval: timedelta = (
            SCAN_INTERVAL_LOCAL
            if self.mode == PWRviewMode.LOCAL
            else SCAN_INTERVAL_CLOUD
        )

        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> PWRviewData:
        """Fetch data from PWRview sensor."""
        try:
            if self.mode == PWRviewMode.LOCAL:
                return await self._fetch_local_data()
            return await self._fetch_cloud_data()
        except PWRviewConnectionError as err:
            raise UpdateFailed(f"Error communicating with PWRview: {err}") from err
        except PWRviewError as err:
            raise UpdateFailed(f"Error fetching PWRview data: {err}") from err

    async def _fetch_local_data(self) -> PWRviewData:
        """Fetch data from local PWRview device."""
        if not self._local_client:
            raise UpdateFailed("No local client configured")

        sample = await self._local_client.get_current_sample()

        channels: dict[PWRviewChannel, PWRviewChannelData] = {}

        channel_type_map = {
            "CONSUMPTION": PWRviewChannel.CONSUMPTION,
            "GENERATION": PWRviewChannel.GENERATION,
            "NET": PWRviewChannel.NET,
            "PHASE_A_CONSUMPTION": PWRviewChannel.PHASE_A,
            "PHASE_B_CONSUMPTION": PWRviewChannel.PHASE_B,
        }

        for channel in sample.channels:
            pwrview_channel = channel_type_map.get(channel.channel_type)

            if pwrview_channel:
                channels[pwrview_channel] = PWRviewChannelData(
                    power=channel.power,
                    energy_imported=(
                        channel.energy_imported / WATT_SECONDS_TO_KWH
                        if channel.energy_imported is not None
                        else None
                    ),
                    energy_exported=(
                        channel.energy_exported / WATT_SECONDS_TO_KWH
                        if channel.energy_exported is not None
                        else None
                    ),
                    voltage=channel.voltage,
                )

        return PWRviewData(
            channels=channels,
            timestamp=sample.timestamp.isoformat() if sample.timestamp else None,
        )

    async def _fetch_cloud_data(self) -> PWRviewData:
        """Fetch data from cloud PWRview API."""
        if not self._cloud_client:
            raise UpdateFailed("Cloud client not initialized")

        # Get current power readings
        live_data = await self._cloud_client.get_live_sample(self.sensor_id)

        # Get today's stats for import/export energy
        start_time = (
            dt_util.start_of_local_day().astimezone(dt_util.UTC).isoformat()
        )
        end_time = dt_util.utcnow().isoformat()
        stats_data = await self._cloud_client.get_stats(
            self.sensor_id, start_time, "days", end_time
        )

        # Get full samples for voltage data
        full_samples = await self._cloud_client.get_samples(
            self.sensor_id, start_time, "hours", end_time, full=True
        )

        return self._parse_cloud_response(live_data, stats_data, full_samples)

    def _parse_cloud_response(
        self,
        live_data: object,
        stats_data: list[object],
        full_samples: list[object],
    ) -> PWRviewData:
        """Parse cloud API responses into PWRviewData."""
        channels: dict[PWRviewChannel, PWRviewChannelData] = {}

        # Parse live data for power readings
        channels[PWRviewChannel.CONSUMPTION] = PWRviewChannelData(
            power=live_data.consumption_power,
            energy_imported=(
                live_data.consumption_energy / WATT_SECONDS_TO_KWH
                if live_data.consumption_energy is not None
                else None
            ),
        )

        channels[PWRviewChannel.GENERATION] = PWRviewChannelData(
            power=live_data.generation_power,
            energy_imported=(
                live_data.generation_energy / WATT_SECONDS_TO_KWH
                if live_data.generation_energy is not None
                else None
            ),
        )

        channels[PWRviewChannel.NET] = PWRviewChannelData(
            power=live_data.net_power,
            energy_imported=(
                live_data.net_energy / WATT_SECONDS_TO_KWH
                if live_data.net_energy is not None
                else None
            ),
        )

        # Add import/export from stats if available
        if stats_data:
            total_imported = sum(
                s.imported_energy for s in stats_data if s.imported_energy is not None
            )
            total_exported = sum(
                s.exported_energy for s in stats_data if s.exported_energy is not None
            )
            channels[PWRviewChannel.NET].energy_imported = (
                total_imported / WATT_SECONDS_TO_KWH
            )
            channels[PWRviewChannel.NET].energy_exported = (
                total_exported / WATT_SECONDS_TO_KWH
            )

        # Add voltage from full samples if available
        if full_samples:
            latest_sample = full_samples[-1]
            self._add_voltage_from_full_sample(channels, latest_sample)

        return PWRviewData(
            channels=channels,
            timestamp=(
                live_data.timestamp.isoformat() if live_data.timestamp else None
            ),
        )

    def _add_voltage_from_full_sample(
        self,
        channels: dict[PWRviewChannel, PWRviewChannelData],
        sample: object,
    ) -> None:
        """Add voltage readings from full sample data."""
        channel_type_map = {
            "phase_a": PWRviewChannel.PHASE_A,
            "phase_b": PWRviewChannel.PHASE_B,
            "consumption": PWRviewChannel.CONSUMPTION,
            "generation": PWRviewChannel.GENERATION,
            "net": PWRviewChannel.NET,
        }

        for channel_sample in sample.channel_samples:
            pwrview_channel = channel_type_map.get(channel_sample.channel_type)

            if pwrview_channel:
                if pwrview_channel not in channels:
                    channels[pwrview_channel] = PWRviewChannelData()

                channels[pwrview_channel].voltage = channel_sample.voltage

                # For phase channels, also add power and energy
                if pwrview_channel in (PWRviewChannel.PHASE_A, PWRviewChannel.PHASE_B):
                    channels[pwrview_channel].power = channel_sample.power
                    channels[pwrview_channel].energy_imported = (
                        channel_sample.energy_imported / WATT_SECONDS_TO_KWH
                        if channel_sample.energy_imported is not None
                        else None
                    )
                    channels[pwrview_channel].energy_exported = (
                        channel_sample.energy_exported / WATT_SECONDS_TO_KWH
                        if channel_sample.energy_exported is not None
                        else None
                    )
