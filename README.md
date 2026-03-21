# Generac PWRview for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)

Home Assistant custom integration for [Generac PWRview](https://www.generac.com/) (formerly Neurio) energy monitors.

Supports both **local polling** (fast, 10-second updates) and **cloud API** access (120-second updates), with automatic detection of the best connection method.

## Features

- **Two setup paths** — cloud API with auto-discovery, or local-only with manual device entry
- **Local-first** — automatically tries local connection for faster polling before falling back to cloud
- **Energy dashboard ready** — grid import/export sensors integrate directly with the HA Energy dashboard
- **11 sensor entities** — consumption, generation, net/grid power and energy, plus phase voltage and power diagnostics
- **Modern architecture** — async coordinator, config flow, device registry, entity translations

## Sensors

| Sensor | Type | Unit |
|--------|------|------|
| Home consumption power | Power | W |
| Home consumption energy | Energy | kWh |
| Solar production power | Power | W |
| Solar production energy | Energy | kWh |
| Grid power | Power | W |
| Grid import energy | Energy | kWh |
| Grid export energy | Energy | kWh |
| Phase A voltage | Diagnostic | V |
| Phase A power | Diagnostic | W |
| Phase B voltage | Diagnostic | V |
| Phase B power | Diagnostic | W |

Phase sensors are disabled by default and can be enabled in the entity settings.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu and select **Custom repositories**
3. Add `https://github.com/W7RZL/ha-generac-pwrview` with category **Integration**
4. Search for "Generac PWRview" and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/generac_pwrview` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

After installation, add the integration via **Settings > Devices & Services > Add Integration > Generac PWRview**.

You'll see two setup options:

### Cloud API

Enter your Generac/Neurio API credentials. The integration will:
1. Discover your device automatically
2. Test local connectivity
3. Use local polling if reachable, otherwise fall back to cloud

To get API credentials, register an application at https://my.neur.io/#settings/applications/register (homepage and callback URLs are optional).

### Local only

Enter your device's IP address and serial number (printed on the dongle). No cloud account needed — connects directly to the device on your network.

## Requirements

- A Generac PWRview or Neurio energy monitor
- For cloud setup: API key and secret from my.neur.io
- For local setup: device IP address and serial number

## Attribution

This integration uses the [generac-pwrview](https://github.com/W7RZL/generac-pwrview-python) Python library, which is a modernized fork of [neurio-python](https://github.com/jordanh/neurio-python) by Jordan Husney.

## License

Apache License 2.0
