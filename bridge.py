import argparse
import asyncio
import logging
import os
import sys
import time

from dotenv import load_dotenv

__version__ = "0.1.0"

load_dotenv("lametric-autarco-bridge.env")

from sinks.lametric import push_to_lametric, push_to_lametric_stale
from sources.solis_modbus import SolisModbusSource

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

STALE_DATA_TIMEOUT = 30


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        logger.error("%s must be an integer", name)
        sys.exit(1)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        logger.error("%s must be a number", name)
        sys.exit(1)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    if value.lower() in {"1", "true", "yes", "on"}:
        return True
    if value.lower() in {"0", "false", "no", "off"}:
        return False

    logger.error("%s must be true or false", name)
    sys.exit(1)


def get_source():
    """Initialize the Solis/Ginlong Modbus RTU source."""
    device = os.getenv("SOLIS_MODBUS_DEVICE", "/dev/ttyUSB0")
    baudrate = _env_int("SOLIS_MODBUS_BAUDRATE", 9600)
    slave_id = _env_int("SOLIS_MODBUS_SLAVE_ID", 1)
    register = _env_int("SOLIS_MODBUS_REGISTER", 3004)
    count = _env_int("SOLIS_MODBUS_REGISTER_COUNT", 2)
    scale = _env_float("SOLIS_MODBUS_SCALE", 1.0)
    poll_interval = _env_float("SOLIS_MODBUS_POLL_INTERVAL", 1.0)
    timeout = _env_float("SOLIS_MODBUS_TIMEOUT", 2.0)
    byteorder = os.getenv("SOLIS_MODBUS_BYTEORDER", "big")
    signed = _env_bool("SOLIS_MODBUS_SIGNED", False)

    logger.info(
        "Using source: Solis/Ginlong Modbus RTU (%s, slave %s, register %s)",
        device,
        slave_id,
        register,
    )

    return SolisModbusSource(
        device=device,
        baudrate=baudrate,
        slave_id=slave_id,
        register=register,
        count=count,
        scale=scale,
        poll_interval=poll_interval,
        timeout=timeout,
        byteorder=byteorder,
        signed=signed,
    )


async def main():
    source = get_source()

    async with source:
        state = {
            "last_reading_time": time.time(),
            "stale_alert_sent": False,
        }

        async def timeout_monitor():
            while True:
                await asyncio.sleep(5)
                time_since_last_reading = time.time() - state["last_reading_time"]

                if time_since_last_reading > STALE_DATA_TIMEOUT:
                    if not state["stale_alert_sent"]:
                        logger.warning("No data received for %ss, pushing stale indicator", STALE_DATA_TIMEOUT)
                        await push_to_lametric_stale()
                        state["stale_alert_sent"] = True
                else:
                    state["stale_alert_sent"] = False

        async def stream_readings():
            while True:
                try:
                    async for reading in source.stream():
                        state["last_reading_time"] = time.time()
                        await push_to_lametric(reading)
                        logger.info("[%s] Generation: %.0f W", reading.timestamp, reading.power_watts)
                except Exception as e:
                    logger.error("Stream error: %s", e)
                    await asyncio.sleep(5)

        async with asyncio.TaskGroup() as task_group:
            task_group.create_task(stream_readings())
            task_group.create_task(timeout_monitor())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LaMetric Autarco/Solis Bridge")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.parse_args()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Script stopped by user.")
