"""LaMetric Time egress module - formats and pushes generation data via HTTP."""
import asyncio
import logging
import os
import requests

from sources.base import GenerationReading

logger = logging.getLogger(__name__)

ICON_SOLAR = 54077
ICON_STALE = 1059

LAMETRIC_API_KEY = os.environ.get("LAMETRIC_API_KEY")
LAMETRIC_URL = os.environ.get("LAMETRIC_URL")


def _make_request_sync(payload):
    response = requests.post(
        LAMETRIC_URL,
        json=payload,
        auth=("dev", LAMETRIC_API_KEY),
        timeout=2,
    )
    response.raise_for_status()


async def send_http_payload(payload):
    """Offload the blocking HTTP request to a thread."""
    if not LAMETRIC_URL:
        logger.warning("LaMetric: LAMETRIC_URL not configured. Skipping push.")
        return

    if not LAMETRIC_API_KEY:
        logger.warning("LaMetric: LAMETRIC_API_KEY not configured. Skipping push.")
        return

    try:
        await asyncio.to_thread(_make_request_sync, payload)
    except Exception as e:
        logger.warning("LaMetric: HTTP POST failed: %s", e)


def format_power(power_watts: float) -> str:
    """Format Watts for the small LaMetric display."""
    power = round(power_watts)

    if abs(power) >= 10000:
        return f"{power / 1000:.1f} kW"

    return f"{power} W"


async def push_to_lametric(reading: GenerationReading):
    """Format generation data and send it to LaMetric Time."""
    payload = {
        "frames": [
            {
                "text": format_power(reading.power_watts),
                "icon": ICON_SOLAR,
                "index": 0,
            }
        ]
    }

    await send_http_payload(payload)


async def push_to_lametric_stale():
    """Push a stale data indicator when no inverter data is received."""
    payload = {
        "frames": [
            {
                "text": "-- W",
                "icon": ICON_STALE,
                "index": 0,
            }
        ]
    }

    await send_http_payload(payload)
