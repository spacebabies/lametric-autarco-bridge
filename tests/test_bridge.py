from unittest.mock import patch

import pytest

import bridge
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
