"""Constants for the Generac PWRview integration."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum
import logging
from typing import Final

DOMAIN: Final = "generac_pwrview"
LOGGER = logging.getLogger(__package__)

# Configuration
CONF_API_SECRET: Final = "api_secret"
CONF_SERIAL_NUMBER: Final = "serial_number"

# Polling intervals
SCAN_INTERVAL_LOCAL: Final = timedelta(seconds=10)
SCAN_INTERVAL_CLOUD: Final = timedelta(seconds=120)

# Unit conversions
WATT_SECONDS_TO_KWH: Final = 3600000  # 1 kWh = 3,600,000 Ws


class PWRviewMode(StrEnum):
    """PWRview connection mode."""

    LOCAL = "local"
    CLOUD = "cloud"


class PWRviewChannel(StrEnum):
    """PWRview channel types."""

    CONSUMPTION = "consumption"
    GENERATION = "generation"
    NET = "net"
    PHASE_A = "phase_a"
    PHASE_B = "phase_b"
