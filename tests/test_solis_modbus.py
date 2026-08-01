import pytest

from sources.solis_modbus import SolisModbusSource


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
