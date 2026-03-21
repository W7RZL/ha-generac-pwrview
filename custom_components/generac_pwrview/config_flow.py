"""Config flow for Generac PWRview integration."""

from __future__ import annotations

from typing import Any

from generac_pwrview import (
    PWRviewAuthError,
    PWRviewClient,
    PWRviewConnectionError,
    PWRviewError,
    PWRviewLocalClient,
)
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_API_SECRET, CONF_SERIAL_NUMBER, DOMAIN, LOGGER, PWRviewMode

STEP_CLOUD_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_API_SECRET): str,
    }
)

STEP_LOCAL_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_SERIAL_NUMBER): str,
    }
)


class PWRviewConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Generac PWRview."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._sensor_id: str | None = None
        self._host: str | None = None
        self._serial_number: str | None = None
        self._location_name: str | None = None
        self._api_key: str | None = None
        self._api_secret: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial menu step."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["cloud", "local"],
        )

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the cloud API credentials step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]
            self._api_secret = user_input[CONF_API_SECRET]

            try:
                await self._async_discover_sensor()
            except PWRviewConnectionError:
                errors["base"] = "cannot_connect"
            except PWRviewAuthError:
                errors["base"] = "invalid_auth"
            except PWRviewError:
                errors["base"] = "cannot_connect"
            else:
                if not self._sensor_id:
                    errors["base"] = "no_sensors"
                else:
                    # Check for duplicate
                    await self.async_set_unique_id(self._serial_number)
                    self._abort_if_unique_id_configured()

                    # Try local connection
                    if self._host and await self._async_test_local_connection():
                        return self._create_entry(PWRviewMode.LOCAL)

                    # Local failed, show options
                    return await self.async_step_local_failed()

        return self.async_show_form(
            step_id="cloud",
            data_schema=STEP_CLOUD_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the local-only setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._serial_number = user_input[CONF_SERIAL_NUMBER]

            # Check for duplicate
            await self.async_set_unique_id(self._serial_number)
            self._abort_if_unique_id_configured()

            # Test local connection
            if await self._async_test_local_connection():
                self._location_name = f"PWRview {self._serial_number}"
                return self._create_entry(PWRviewMode.LOCAL)

            errors["base"] = "local_connection_failed"

        return self.async_show_form(
            step_id="local",
            data_schema=STEP_LOCAL_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_local_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the local connection failed step."""
        if user_input is not None:
            if user_input.get("use_cloud"):
                return self._create_entry(PWRviewMode.CLOUD)
            # Retry local connection
            if await self._async_test_local_connection():
                return self._create_entry(PWRviewMode.LOCAL)
            # Still failed, show form again
            return self.async_show_form(
                step_id="local_failed",
                data_schema=vol.Schema(
                    {
                        vol.Required("use_cloud", default=False): bool,
                    }
                ),
                description_placeholders={"host": self._host or "unknown"},
                errors={"base": "local_connection_failed"},
            )

        return self.async_show_form(
            step_id="local_failed",
            data_schema=vol.Schema(
                {
                    vol.Required("use_cloud", default=False): bool,
                }
            ),
            description_placeholders={"host": self._host or "unknown"},
        )

    def _create_entry(self, mode: PWRviewMode) -> ConfigFlowResult:
        """Create the config entry."""
        return self.async_create_entry(
            title=self._location_name or "PWRview",
            data={
                CONF_API_KEY: self._api_key,
                CONF_API_SECRET: self._api_secret,
                "sensor_id": self._sensor_id,
                CONF_HOST: self._host,
                "serial_number": self._serial_number,
                "location_name": self._location_name,
                "mode": mode,
            },
        )

    async def _async_discover_sensor(self) -> None:
        """Discover sensor via cloud API."""
        session = async_get_clientsession(self.hass)
        client = PWRviewClient(
            api_key=self._api_key,
            api_secret=self._api_secret,
            session=session,
        )

        user_info = await client.get_user_information()

        # Use the first location with sensors
        for location in user_info.locations:
            if location.sensors:
                sensor = location.sensors[0]
                self._sensor_id = sensor.sensor_id
                self._host = sensor.ip_address
                self._serial_number = sensor.serial_number
                self._location_name = location.name
                return

    async def _async_test_local_connection(self) -> bool:
        """Test local connection to PWRview device."""
        if not self._host:
            return False

        session = async_get_clientsession(self.hass)
        client = PWRviewLocalClient(host=self._host, session=session)

        try:
            await client.get_current_sample()
        except PWRviewError:
            LOGGER.debug("Local connection to %s failed", self._host)
            return False
        return True
