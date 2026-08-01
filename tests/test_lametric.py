import pytest

from sinks.lametric import format_power, push_to_lametric, push_to_lametric_stale
from sources.base import GenerationReading


def test_format_power_watts():
    assert format_power(3517.2) == "3517 W"


def test_format_power_kilowatts():
    assert format_power(10500) == "10.5 kW"


@pytest.mark.asyncio
async def test_push_to_lametric(mocker):
    mock_send = mocker.patch("sinks.lametric.send_http_payload")

    await push_to_lametric(GenerationReading(power_watts=1800.7))

    mock_send.assert_called_once_with(
        {
            "frames": [
                {
                    "text": "1801 W",
                    "icon": 54077,
                    "index": 0,
                }
            ]
        }
    )


@pytest.mark.asyncio
async def test_push_to_lametric_stale(mocker):
    mock_send = mocker.patch("sinks.lametric.send_http_payload")

    await push_to_lametric_stale()

    mock_send.assert_called_once_with(
        {
            "frames": [
                {
                    "text": "-- W",
                    "icon": 1059,
                    "index": 0,
                }
            ]
        }
    )
