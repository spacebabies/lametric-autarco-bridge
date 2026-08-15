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

### Finding The USB RS485 Adapter

Do not select an adapter from its `/dev/ttyUSB0` number. That number is assigned
when devices are detected and may change after a reboot or when another USB
serial device is connected. P1 smart-meter cables, console cables and RS485
adapters can also use the same FTDI USB chip, so even identical `lsusb` entries
do not prove which cable is which.

The most reliable procedure is to identify the adapter while it is the only USB
serial cable being connected:

1. Stop programs which use any USB serial cables, then disconnect the other
   serial cables temporarily. If that is impractical, record the list before
   connecting the RS485 adapter.

   ```bash
   ls -l /dev/serial/by-id/ 2>/dev/null
   ```

2. Connect the USB RS485 adapter and run the command again. The newly appearing
   entry is the adapter. For example:

   ```text
   usb-FTDI_FT232R_USB_UART_BG03OE3O-if00-port0 -> ../../ttyUSB0
   ```

   The part before `->` is the stable device name. It will be different for
   each adapter; copy it exactly from your own output.

3. Put its complete path in `lametric-autarco-bridge.env`:

   ```dotenv
   SOLIS_MODBUS_DEVICE=/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BG03OE3O-if00-port0
   SOLIS_MODBUS_BAUDRATE=9600
   SOLIS_MODBUS_SLAVE_ID=1
   ```

4. Reconnect the other cables and confirm that the selected symlink still
   resolves to an existing device:

   ```bash
   readlink -f /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_BG03OE3O-if00-port0
   ```

   Output such as `/dev/ttyUSB0` or `/dev/ttyUSB1` is expected. It does not
   matter if that final number changes later: the configured `by-id` path stays
   associated with the adapter's USB serial number.

5. Test only the selected adapter and Modbus connection:

   ```bash
   python bridge.py --modbus-only
   ```

   This bridge only reads Modbus registers. A wrong serial device normally
   results in timeouts or invalid responses, but it is still better to identify
   the cable physically instead of trying every serial port on the system.

For additional diagnosis, list all USB devices and serial ports:

```bash
lsusb
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
ls -l /dev/serial/by-id/ 2>/dev/null
```

An RS485 adapter may appear as an FTDI, CH340/CH341, CP210x or Prolific device.
USB vendor/product IDs from `lsusb`, such as `0403:6001`, do not need separate
env settings. If no new serial device appears, follow kernel messages while
reconnecting the adapter:

```bash
sudo dmesg --follow
```

The kernel should report a device such as `ttyUSB0` or `ttyACM0`. Its USB
properties can be inspected with:

```bash
udevadm info --query=property --name=/dev/ttyUSB0
```

## Run Manually

```bash
source .venv/bin/activate
python bridge.py
```

To test only the USB/Modbus connection, without configuring or contacting a
LaMetric device:

```bash
python bridge.py --modbus-only
```

This continuously writes timestamped power readings to stdout. Stop it with
`Ctrl-C`. Only the `SOLIS_MODBUS_*` settings are used in this mode.

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
