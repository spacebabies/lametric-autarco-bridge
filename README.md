# LaMetric Autarco/Solis Bridge

Local RS485-to-LaMetric bridge for showing realtime solar generation from an Autarco-branded inverter that speaks Solis/Ginlong-ish Modbus RTU.

This is deliberately simpler than `lametric-power-bridge`: one ingress path, one display target, no cloud.

## What It Does

- Polls the inverter over a USB RS485 adapter using Modbus RTU.
- Reads a configurable active-power holding register.
- Pushes the current generation to a LaMetric Time using the local HTTP Push URL.
- Shows `-- W` if data goes stale.
- Runs cleanly under systemd on a small Linux box.

## Hardware

- LaMetric Time with the **My Data DIY** app configured for HTTP Push.
- USB RS485 adapter.
- Twisted pair from adapter A/B to the inverter RS485 A/B terminals.
- Correct serial permissions for the service user, usually membership of `dialout`.

## Register Assumptions

Public Solis/Ginlong register maps are annoyingly inconsistent across model families and tools.

The default is:

```text
SOLIS_MODBUS_REGISTER=3004
SOLIS_MODBUS_REGISTER_COUNT=2
SOLIS_MODBUS_SCALE=1.0
SOLIS_MODBUS_BYTEORDER=big
SOLIS_MODBUS_SIGNED=false
```

That matches commonly documented Solis string inverter active power at registers `3004, 3005`.

For many hybrid models, try:

```text
SOLIS_MODBUS_REGISTER=33079
SOLIS_MODBUS_REGISTER_COUNT=2
```

Some Modbus tools show one-based register numbers while libraries use zero-based addresses. This bridge sends `SOLIS_MODBUS_REGISTER` directly to `pymodbus`. If the read fails or the values look shifted, try one lower: `3003` or `33078`.

Useful references:

- Solis Modbus integration register overview: https://solis-modbus.readthedocs.io/en/latest/sensors.html
- Solis service note showing function code 03 and starting address `3000`: https://usservice.solisinverters.com/support/solutions/articles/73000660897-modbus-tcp-ip

## Installation

```bash
git clone git@github.com:spacebabies/lametric-autarco-bridge.git
cd lametric-autarco-bridge

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

```bash
cp lametric-autarco-bridge.env.example lametric-autarco-bridge.env
vim lametric-autarco-bridge.env
```

Required:

- `LAMETRIC_URL`: full HTTP Push URL from the LaMetric mobile app.
- `LAMETRIC_API_KEY`: local API key for the device.
- `SOLIS_MODBUS_DEVICE`: USB RS485 adapter path, default `/dev/ttyUSB0`.

Common Modbus defaults:

- `SOLIS_MODBUS_BAUDRATE=9600`
- `SOLIS_MODBUS_SLAVE_ID=1`
- `SOLIS_MODBUS_REGISTER=3004`
- `SOLIS_MODBUS_REGISTER_COUNT=2`

## Run Manually

```bash
source .venv/bin/activate
python bridge.py
```

If the serial adapter is not accessible:

```bash
ls -la /dev/ttyUSB*
sudo usermod -a -G dialout "$USER"
```

Then log out and back in.

## Running As A Service

Edit `lametric-autarco-bridge.service` for your username and path, then:

```bash
sudo cp lametric-autarco-bridge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lametric-autarco-bridge
sudo journalctl -u lametric-autarco-bridge -f
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Notes

This only reads registers. It does not write settings to the inverter.

## License

GPLv3.
