"""Solis/Ginlong Modbus RTU ingress module."""
import asyncio
import inspect
import logging
import sys
from datetime import datetime, timezone
from typing import AsyncIterator

try:
    from pymodbus.client import AsyncModbusSerialClient
except ImportError:
    AsyncModbusSerialClient = None

from sources.base import GenerationReading

logger = logging.getLogger(__name__)


class SolisModbusSource:
    """
    Reads realtime generation from a Solis/Ginlong inverter over RS485 Modbus RTU.

    Default register assumptions target common Solis string inverter maps:
    - holding register 3004, length 2
    - unsigned 32-bit big-endian value
    - scale factor 1.0, unit W

    Hybrid models commonly expose comparable active power at 33079/33080.
    Keep the register configurable; Autarco branding does not guarantee one map.
    """

    def __init__(
        self,
        device: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
        slave_id: int = 1,
        register: int = 3004,
        count: int = 2,
        scale: float = 1.0,
        poll_interval: float = 1.0,
        timeout: float = 2.0,
        byteorder: str = "big",
        signed: bool = False,
    ):
        if AsyncModbusSerialClient is None:
            logger.error("pymodbus library not installed. Run: pip install -r requirements.txt")
            sys.exit(1)

        self.device = device
        self.baudrate = baudrate
        self.slave_id = slave_id
        self.register = register
        self.count = count
        self.scale = scale
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.byteorder = byteorder
        self.signed = signed
        self.client = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()
            logger.info("Solis Modbus: Port closed")

    async def connect(self) -> None:
        """Open the serial Modbus client and verify that the target register responds."""
        if not self.device:
            logger.error("SOLIS_MODBUS_DEVICE not configured")
            sys.exit(1)
            return

        logger.info(
            "Solis Modbus: Opening %s at %s baud, slave %s",
            self.device,
            self.baudrate,
            self.slave_id,
        )

        self.client = AsyncModbusSerialClient(
            port=self.device,
            baudrate=self.baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=self.timeout,
        )

        connected = await self.client.connect()
        if not connected:
            logger.error("Solis Modbus: Cannot open %s", self.device)
            sys.exit(1)
            return

        reading = await self.read_power()
        logger.info("Solis Modbus: Connection successful. Current output: %.0f W", reading.power_watts)

    async def stream(self) -> AsyncIterator[GenerationReading]:
        """Poll the configured Modbus register forever."""
        if self.client is None:
            logger.error("Solis Modbus: stream() called before connect()")
            return

        logger.info(
            "Solis Modbus: Polling holding register %s (%s register%s) every %.1fs",
            self.register,
            self.count,
            "" if self.count == 1 else "s",
            self.poll_interval,
        )

        while True:
            try:
                yield await self.read_power()
            except Exception as e:
                logger.error("Solis Modbus: Read failed: %s", e)

            await asyncio.sleep(self.poll_interval)

    async def read_power(self) -> GenerationReading:
        """Read one power value from the configured holding register."""
        if self.client is None:
            raise RuntimeError("Modbus client is not connected")

        parameters = inspect.signature(self.client.read_holding_registers).parameters
        unit_argument = "device_id" if "device_id" in parameters else "slave"
        result = await self.client.read_holding_registers(
            address=self.register,
            count=self.count,
            **{unit_argument: self.slave_id},
        )

        if result.isError():
            raise RuntimeError(f"Modbus exception response: {result}")

        raw_value = self.decode_registers(
            result.registers,
            byteorder=self.byteorder,
            signed=self.signed,
        )

        return GenerationReading(
            power_watts=raw_value * self.scale,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def decode_registers(registers: list[int], byteorder: str = "big", signed: bool = False) -> int:
        """Decode one or more 16-bit Modbus registers into an integer."""
        if not registers:
            raise ValueError("At least one register is required")

        if byteorder not in {"big", "little"}:
            raise ValueError("byteorder must be 'big' or 'little'")

        ordered_registers = registers if byteorder == "big" else list(reversed(registers))
        value = 0
        for register in ordered_registers:
            if register < 0 or register > 0xFFFF:
                raise ValueError(f"Invalid 16-bit register value: {register}")
            value = (value << 16) | register

        bit_count = len(registers) * 16
        sign_bit = 1 << (bit_count - 1)
        if signed and value & sign_bit:
            value -= 1 << bit_count

        return value
