"""Live test script for generac-pwrview library.

Usage:
    # Local only (no credentials needed):
    python test_live.py --host 192.168.42.18

    # Cloud API (reads credentials from .env or environment):
    export PWRVIEW_API_KEY=your_key
    export PWRVIEW_API_SECRET=your_secret
    python test_live.py --cloud

    # Both:
    python test_live.py --host 192.168.42.18 --cloud
"""

import argparse
import asyncio
import os
import sys

import aiohttp
from generac_pwrview import (
    PWRviewClient,
    PWRviewError,
    PWRviewLocalClient,
)


async def test_local(host: str) -> bool:
    """Test local device connection."""
    print(f"\n{'='*60}")
    print(f"Testing local connection to {host}")
    print(f"{'='*60}")

    async with aiohttp.ClientSession() as session:
        client = PWRviewLocalClient(host=host, session=session)
        try:
            sample = await client.get_current_sample()
        except PWRviewError as err:
            print(f"FAILED: {err}")
            return False

    print(f"Timestamp: {sample.timestamp}")
    print(f"Channels:  {len(sample.channels)}")
    print()

    for ch in sample.channels:
        print(f"  [{ch.channel_type}]")
        print(f"    Power:           {ch.power} W")
        print(f"    Voltage:         {ch.voltage} V")
        print(f"    Energy imported: {ch.energy_imported} Ws", end="")
        if ch.energy_imported is not None:
            print(f" ({ch.energy_imported / 3600000:.2f} kWh)")
        else:
            print()
        print(f"    Energy exported: {ch.energy_exported} Ws", end="")
        if ch.energy_exported is not None:
            print(f" ({ch.energy_exported / 3600000:.2f} kWh)")
        else:
            print()
        print()

    print("LOCAL TEST: PASSED")
    return True


async def test_cloud() -> bool:
    """Test cloud API connection."""
    api_key = os.environ.get("PWRVIEW_API_KEY")
    api_secret = os.environ.get("PWRVIEW_API_SECRET")

    if not api_key or not api_secret:
        print("\nSkipping cloud test: PWRVIEW_API_KEY and PWRVIEW_API_SECRET not set")
        return True

    print(f"\n{'='*60}")
    print("Testing cloud API connection")
    print(f"{'='*60}")

    async with aiohttp.ClientSession() as session:
        client = PWRviewClient(api_key=api_key, api_secret=api_secret, session=session)

        try:
            user_info = await client.get_user_information()
        except PWRviewError as err:
            print(f"FAILED to get user info: {err}")
            return False

        print(f"Locations: {len(user_info.locations)}")
        for loc in user_info.locations:
            print(f"  [{loc.name}]")
            for sensor in loc.sensors:
                print(f"    Sensor ID:     {sensor.sensor_id}")
                print(f"    Serial:        {sensor.serial_number}")
                print(f"    IP:            {sensor.ip_address}")
            print()

        # Test live sample from first sensor
        if user_info.locations and user_info.locations[0].sensors:
            sensor_id = user_info.locations[0].sensors[0].sensor_id
            print(f"Fetching live sample for sensor {sensor_id}...")

            try:
                live = await client.get_live_sample(sensor_id)
            except PWRviewError as err:
                print(f"FAILED to get live sample: {err}")
                return False

            print(f"  Timestamp:          {live.timestamp}")
            print(f"  Consumption power:  {live.consumption_power} W")
            print(f"  Generation power:   {live.generation_power} W")
            print(f"  Net power:          {live.net_power} W")
            print(f"  Consumption energy: {live.consumption_energy} Ws")
            print(f"  Generation energy:  {live.generation_energy} Ws")
            print(f"  Net energy:         {live.net_energy} Ws")
            print()

            # Test stats (today's energy totals)
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            start = start_of_day.isoformat()
            end = now.isoformat()

            print(f"Fetching stats for today ({start_of_day.date()})...")
            try:
                stats = await client.get_stats(sensor_id, start, "days", end)
            except PWRviewError as err:
                print(f"FAILED to get stats: {err}")
                return False

            print(f"  Stats entries: {len(stats)}")
            for i, s in enumerate(stats):
                print(f"  [{i}] start={s.start} end={s.end}")
                print(f"      Consumption:  {s.consumption_energy} Ws", end="")
                if s.consumption_energy is not None:
                    print(f" ({s.consumption_energy / 3600000:.2f} kWh)")
                else:
                    print()
                print(f"      Generation:   {s.generation_energy} Ws", end="")
                if s.generation_energy is not None:
                    print(f" ({s.generation_energy / 3600000:.2f} kWh)")
                else:
                    print()
                print(f"      Imported:     {s.imported_energy} Ws", end="")
                if s.imported_energy is not None:
                    print(f" ({s.imported_energy / 3600000:.2f} kWh)")
                else:
                    print()
                print(f"      Exported:     {s.exported_energy} Ws", end="")
                if s.exported_energy is not None:
                    print(f" ({s.exported_energy / 3600000:.2f} kWh)")
                else:
                    print()
            print()

            # Test full samples (voltage/phase data)
            print("Fetching full samples (last hour)...")
            hour_ago = (now.timestamp() - 3600)
            hour_start = datetime.fromtimestamp(hour_ago, tz=timezone.utc).isoformat()

            try:
                samples = await client.get_samples(
                    sensor_id, hour_start, "hours", end, full=True
                )
            except PWRviewError as err:
                print(f"FAILED to get full samples: {err}")
                return False

            print(f"  Full sample entries: {len(samples)}")
            if samples:
                latest = samples[-1]
                print(f"  Latest timestamp: {latest.timestamp}")
                print(f"  Channel samples:  {len(latest.channel_samples)}")
                for ch in latest.channel_samples:
                    print(f"    [{ch.channel_type}]")
                    print(f"      Power:           {ch.power} W")
                    print(f"      Voltage:         {ch.voltage} V")
                    print(f"      Energy imported: {ch.energy_imported} Ws")
                    print(f"      Energy exported: {ch.energy_exported} Ws")
            print()

    print("CLOUD TEST: PASSED")
    return True


async def main() -> int:
    """Run live tests."""
    parser = argparse.ArgumentParser(description="Live test for generac-pwrview")
    parser.add_argument("--host", help="Local device IP address")
    parser.add_argument("--cloud", action="store_true", help="Test cloud API")
    args = parser.parse_args()

    if not args.host and not args.cloud:
        parser.print_help()
        return 1

    results = []

    if args.host:
        results.append(await test_local(args.host))

    if args.cloud:
        results.append(await test_cloud())

    print(f"\n{'='*60}")
    if all(results):
        print("ALL TESTS PASSED")
        return 0

    print("SOME TESTS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
