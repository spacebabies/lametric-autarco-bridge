import pytest
from unittest.mock import AsyncMock, Mock

import sources.solis_modbus as solis_modbus
from sources.solis_modbus import ModbusConnectionError, SolisModbusSource


class RecentModbusClient:
    def __init__(self):
        self.read = AsyncMock(
            return_value=Mock(registers=[0, 1234], isError=Mock(return_value=False)),
        )

    async def read_holding_registers(self, address, *, count=1, device_id=1):
        return await self.read(address=address, count=count, device_id=device_id)


class LegacyModbusClient:
    def __init__(self):
        self.read = AsyncMock(
            return_value=Mock(registers=[0, 1234], isError=Mock(return_value=False)),
        )

    async def read_holding_registers(self, address, count=1, slave=1):
        return await self.read(address=address, count=count, slave=slave)


class FailingModbusClient:
    instance = None

    def __init__(self, **kwargs):
        self.closed = False
        self.read_holding_registers = AsyncMock(side_effect=TimeoutError("no response"))
        type(self).instance = self

    async def connect(self):
        return True

    def close(self):
        self.closed = True


def test_decode_single_register():
    assert SolisModbusSource.decode_registers([1234]) == 1234


def test_decode_two_registers_big_endian():
    assert SolisModbusSource.decode_registers([0x0001, 0x86A0]) == 100000


def test_decode_two_registers_little_endian():
    assert SolisModbusSource.decode_registers([0x86A0, 0x0001], byteorder="little") == 100000


def test_decode_signed_negative_value():
    assert SolisModbusSource.decode_registers([0xFFFF, 0xFC18], signed=True) == -1000


def test_decode_rejects_invalid_byteorder():
    with pytest.raises(ValueError):
        SolisModbusSource.decode_registers([1], byteorder="middle")


def test_decode_rejects_invalid_register_value():
    with pytest.raises(ValueError):
        SolisModbusSource.decode_registers([0x10000])


@pytest.mark.asyncio
async def test_read_power_uses_device_id_with_recent_pymodbus_api(monkeypatch):
    monkeypatch.setattr(solis_modbus, "AsyncModbusSerialClient", RecentModbusClient)
    source = SolisModbusSource(register=3004, count=2, slave_id=7)
    source.client = RecentModbusClient()

    reading = await source.read_power()

    assert reading.power_watts == 1234
    source.client.read.assert_awaited_once_with(
        address=3004,
        count=2,
        device_id=7,
    )


@pytest.mark.asyncio
async def test_read_power_uses_slave_with_legacy_pymodbus_api(monkeypatch):
    monkeypatch.setattr(solis_modbus, "AsyncModbusSerialClient", LegacyModbusClient)
    source = SolisModbusSource(register=3004, count=2, slave_id=7)
    source.client = LegacyModbusClient()

    reading = await source.read_power()

    assert reading.power_watts == 1234
    source.client.read.assert_awaited_once_with(
        address=3004,
        count=2,
        slave=7,
    )


@pytest.mark.asyncio
async def test_connect_reports_request_context_and_closes_client(monkeypatch):
    monkeypatch.setattr(solis_modbus, "AsyncModbusSerialClient", FailingModbusClient)
    source = SolisModbusSource(
        device="/dev/serial/by-id/test-adapter",
        baudrate=9600,
        slave_id=7,
        register=3004,
    )

    with pytest.raises(ModbusConnectionError) as exc_info:
        await source.connect()

    message = str(exc_info.value)
    assert "/dev/serial/by-id/test-adapter" in message
    assert "slave 7" in message
    assert "register 3004" in message
    assert "9600 baud" in message
    assert "RS485 A/B wiring" in message
    assert "no response" in message
    assert FailingModbusClient.instance.closed is True
