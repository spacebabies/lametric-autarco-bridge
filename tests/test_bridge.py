from unittest.mock import AsyncMock, patch

import pytest

import bridge
from sources.base import GenerationReading
from sources.solis_modbus import SolisModbusSource


def test_get_source_defaults(monkeypatch):
    monkeypatch.delenv("SOLIS_MODBUS_DEVICE", raising=False)
    monkeypatch.delenv("SOLIS_MODBUS_BAUDRATE", raising=False)
    monkeypatch.delenv("SOLIS_MODBUS_SLAVE_ID", raising=False)
    monkeypatch.delenv("SOLIS_MODBUS_REGISTER", raising=False)

    with patch("sources.solis_modbus.AsyncModbusSerialClient", object()):
        source = bridge.get_source()

    assert isinstance(source, SolisModbusSource)
    assert source.device == "/dev/ttyUSB0"
    assert source.baudrate == 9600
    assert source.slave_id == 1
    assert source.register == 3004
    assert source.count == 2


def test_get_source_hybrid_register(monkeypatch):
    monkeypatch.setenv("SOLIS_MODBUS_REGISTER", "33079")
    monkeypatch.setenv("SOLIS_MODBUS_SIGNED", "true")

    with patch("sources.solis_modbus.AsyncModbusSerialClient", object()):
        source = bridge.get_source()

    assert source.register == 33079
    assert source.signed is True


def test_get_source_rejects_invalid_int(monkeypatch):
    monkeypatch.setenv("SOLIS_MODBUS_REGISTER", "not-a-number")

    with pytest.raises(SystemExit) as exc_info:
        bridge.get_source()

    assert exc_info.value.code == 1


def test_parse_args_enables_modbus_only():
    assert bridge.parse_args(["--modbus-only"]).modbus_only is True


@pytest.mark.asyncio
async def test_modbus_only_streams_to_stdout_without_lametric(capsys):
    reading = GenerationReading(power_watts=1234.5, timestamp="2026-08-15T12:00:00+00:00")

    class FakeSource:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def stream(self):
            yield reading

    with (
        patch("bridge.get_source", return_value=FakeSource()),
        patch("bridge.push_to_lametric", new=AsyncMock()) as push,
        patch("bridge.push_to_lametric_stale", new=AsyncMock()) as push_stale,
    ):
        await bridge.main(modbus_only=True)

    assert capsys.readouterr().out == "2026-08-15T12:00:00+00:00 1234.5 W\n"
    push.assert_not_awaited()
    push_stale.assert_not_awaited()
