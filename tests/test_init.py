"""Tests for the Generac PWRview integration setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from generac_pwrview import PWRviewConnectionError
import pytest

from homeassistant.components.generac_pwrview.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("mock_local_client")
async def test_setup_local_entry(
    hass: HomeAssistant,
    init_local_integration: MockConfigEntry,
) -> None:
    """Test successful setup of a local mode config entry."""
    assert init_local_integration.state is ConfigEntryState.LOADED


@pytest.mark.usefixtures("mock_cloud_client")
async def test_setup_cloud_entry(
    hass: HomeAssistant,
    init_cloud_integration: MockConfigEntry,
) -> None:
    """Test successful setup of a cloud mode config entry."""
    assert init_cloud_integration.state is ConfigEntryState.LOADED


@pytest.mark.usefixtures("mock_local_client")
async def test_unload_entry(
    hass: HomeAssistant,
    init_local_integration: MockConfigEntry,
) -> None:
    """Test unloading a config entry."""
    assert init_local_integration.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(init_local_integration.entry_id)
    await hass.async_block_till_done()

    assert init_local_integration.state is ConfigEntryState.NOT_LOADED


async def test_setup_entry_connection_error(
    hass: HomeAssistant,
    mock_config_entry_local: MockConfigEntry,
) -> None:
    """Test setup fails gracefully when device is unreachable."""
    mock_config_entry_local.add_to_hass(hass)

    with patch(
        "homeassistant.components.generac_pwrview.coordinator.PWRviewLocalClient",
        autospec=True,
    ) as mock_cls:
        client = mock_cls.return_value
        client.get_current_sample = AsyncMock(
            side_effect=PWRviewConnectionError("Connection failed")
        )

        await hass.config_entries.async_setup(mock_config_entry_local.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry_local.state is ConfigEntryState.SETUP_RETRY
