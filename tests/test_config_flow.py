"""Tests for the Generac PWRview config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from generac_pwrview import (
    PWRviewAuthError,
    PWRviewConnectionError,
    UserInfo,
)
import pytest

from homeassistant.components.generac_pwrview.const import (
    CONF_API_SECRET,
    CONF_SERIAL_NUMBER,
    DOMAIN,
    PWRviewMode,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import (
    MOCK_API_KEY,
    MOCK_API_SECRET,
    MOCK_HOST,
    MOCK_LOCATION,
    MOCK_SERIAL,
    _make_user_info,
)


async def test_user_flow_shows_menu(hass: HomeAssistant) -> None:
    """Test that the user step shows a menu with cloud and local options."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"
    assert "cloud" in result["menu_options"]
    assert "local" in result["menu_options"]


async def test_cloud_flow_success_with_local(hass: HomeAssistant) -> None:
    """Test cloud flow that auto-detects local connectivity."""
    mock_cloud = AsyncMock()
    mock_cloud.get_user_information = AsyncMock(return_value=_make_user_info())

    mock_local = AsyncMock()
    mock_local.get_current_sample = AsyncMock()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with (
        patch(
            "homeassistant.components.generac_pwrview.config_flow.PWRviewClient",
            return_value=mock_cloud,
        ),
        patch(
            "homeassistant.components.generac_pwrview.config_flow.PWRviewLocalClient",
            return_value=mock_local,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"next_step_id": "cloud"},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "cloud"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_API_SECRET: MOCK_API_SECRET},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_LOCATION
    assert result["data"]["mode"] == PWRviewMode.LOCAL
    assert result["data"][CONF_HOST] == MOCK_HOST
    assert result["data"]["serial_number"] == MOCK_SERIAL
    assert result["data"][CONF_API_KEY] == MOCK_API_KEY
    assert result["data"]["sensor_id"] is not None


async def test_cloud_flow_local_fails_choose_cloud(hass: HomeAssistant) -> None:
    """Test cloud flow when local fails and user chooses cloud mode."""
    mock_cloud = AsyncMock()
    mock_cloud.get_user_information = AsyncMock(return_value=_make_user_info())

    mock_local = AsyncMock()
    mock_local.get_current_sample = AsyncMock(
        side_effect=PWRviewConnectionError("Connection failed")
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with (
        patch(
            "homeassistant.components.generac_pwrview.config_flow.PWRviewClient",
            return_value=mock_cloud,
        ),
        patch(
            "homeassistant.components.generac_pwrview.config_flow.PWRviewLocalClient",
            return_value=mock_local,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"next_step_id": "cloud"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_API_SECRET: MOCK_API_SECRET},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "local_failed"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"use_cloud": True},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["mode"] == PWRviewMode.CLOUD


async def test_cloud_flow_local_fails_retry_succeeds(hass: HomeAssistant) -> None:
    """Test cloud flow when local fails, user retries, and it succeeds."""
    mock_cloud = AsyncMock()
    mock_cloud.get_user_information = AsyncMock(return_value=_make_user_info())

    call_count = 0

    async def _local_side_effect():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise PWRviewConnectionError("Connection failed")

    mock_local = AsyncMock()
    mock_local.get_current_sample = AsyncMock(side_effect=_local_side_effect)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with (
        patch(
            "homeassistant.components.generac_pwrview.config_flow.PWRviewClient",
            return_value=mock_cloud,
        ),
        patch(
            "homeassistant.components.generac_pwrview.config_flow.PWRviewLocalClient",
            return_value=mock_local,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"next_step_id": "cloud"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_API_SECRET: MOCK_API_SECRET},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "local_failed"

        # Retry with use_cloud=False
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"use_cloud": False},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["mode"] == PWRviewMode.LOCAL


async def test_cloud_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test cloud flow with connection error."""
    mock_cloud = AsyncMock()
    mock_cloud.get_user_information = AsyncMock(
        side_effect=PWRviewConnectionError("Connection failed")
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "homeassistant.components.generac_pwrview.config_flow.PWRviewClient",
        return_value=mock_cloud,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"next_step_id": "cloud"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_API_SECRET: MOCK_API_SECRET},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_cloud_flow_invalid_auth(hass: HomeAssistant) -> None:
    """Test cloud flow with authentication error."""
    mock_cloud = AsyncMock()
    mock_cloud.get_user_information = AsyncMock(
        side_effect=PWRviewAuthError("Invalid credentials")
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "homeassistant.components.generac_pwrview.config_flow.PWRviewClient",
        return_value=mock_cloud,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"next_step_id": "cloud"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_API_SECRET: MOCK_API_SECRET},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_cloud_flow_no_sensors(hass: HomeAssistant) -> None:
    """Test cloud flow when no sensors found on account."""
    mock_cloud = AsyncMock()
    mock_cloud.get_user_information = AsyncMock(
        return_value=UserInfo(locations=[])
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "homeassistant.components.generac_pwrview.config_flow.PWRviewClient",
        return_value=mock_cloud,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"next_step_id": "cloud"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_API_SECRET: MOCK_API_SECRET},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_sensors"}


async def test_local_flow_success(hass: HomeAssistant) -> None:
    """Test successful local-only flow."""
    mock_local = AsyncMock()
    mock_local.get_current_sample = AsyncMock()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "homeassistant.components.generac_pwrview.config_flow.PWRviewLocalClient",
        return_value=mock_local,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"next_step_id": "local"},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "local"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_SERIAL_NUMBER: MOCK_SERIAL},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["mode"] == PWRviewMode.LOCAL
    assert result["data"][CONF_HOST] == MOCK_HOST
    assert result["data"]["serial_number"] == MOCK_SERIAL
    assert result["data"][CONF_API_KEY] is None
    assert result["data"]["sensor_id"] is None


async def test_local_flow_connection_failed(hass: HomeAssistant) -> None:
    """Test local flow when device is unreachable."""
    mock_local = AsyncMock()
    mock_local.get_current_sample = AsyncMock(
        side_effect=PWRviewConnectionError("Connection failed")
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "homeassistant.components.generac_pwrview.config_flow.PWRviewLocalClient",
        return_value=mock_local,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"next_step_id": "local"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_SERIAL_NUMBER: MOCK_SERIAL},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "local_connection_failed"}


async def test_duplicate_serial_aborts(
    hass: HomeAssistant,
    mock_config_entry_local: MockConfigEntry,
) -> None:
    """Test that duplicate serial numbers abort the flow."""
    mock_config_entry_local.add_to_hass(hass)

    mock_local = AsyncMock()
    mock_local.get_current_sample = AsyncMock()

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "homeassistant.components.generac_pwrview.config_flow.PWRviewLocalClient",
        return_value=mock_local,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"next_step_id": "local"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_SERIAL_NUMBER: MOCK_SERIAL},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_duplicate_serial_aborts_cloud(
    hass: HomeAssistant,
    mock_config_entry_cloud: MockConfigEntry,
) -> None:
    """Test that duplicate serial numbers abort the cloud flow."""
    mock_config_entry_cloud.add_to_hass(hass)

    mock_cloud = AsyncMock()
    mock_cloud.get_user_information = AsyncMock(return_value=_make_user_info())

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with patch(
        "homeassistant.components.generac_pwrview.config_flow.PWRviewClient",
        return_value=mock_cloud,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"next_step_id": "cloud"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_API_SECRET: MOCK_API_SECRET},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
