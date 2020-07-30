# tinderboxpedal
BT "Universal Remote" Control Code for Digital Guitar Amps

* So far only tested to run on the latest Raspberry Pi OS 32-bit lite image on Pi Zero W and Pi 4B (https://www.raspberrypi.org/downloads/raspberry-pi-os/).
* `setupLinux.sh` will install necessary Python, I2C, BT, and GPIO libraries.
* Add `DisablePlugins = pnat` to `/etc/bluetooth/main.conf` post setup install to ensure proper BT pairing.
* Make sure I2C and Bluetooth are enabled, SSH is recommended for headless development
On client, edit `tinderbox.py` to match your GPIO mapping or OLED screen type before running.

On demo server, edit `demoLedServer.py` to match your LED GPIO mapping before running.

## Basic Schematic:
![](src/tinderbox_hat.png)

## Essential Parts Needed:
- Raspberry Pi Zero W
- SD Card (at least 8GB)
- Pi Power Supply
- 128x64 I2C OLED
- 4 SPST Normally Open Momentary Switches
