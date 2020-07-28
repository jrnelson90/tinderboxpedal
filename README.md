# tinderboxpedal
BT "Universal Remote" Control Code for Digital Guitar Amps

* So far only tested to run on the latest Raspberry Pi OS 32-bit lite image on Pi Zero W and Pi 4B (https://www.raspberrypi.org/downloads/raspberry-pi-os/).
* `setupLinux.sh` will install necessary Python, I2C, BT, and GPIO libraries.
* Add `DisablePlugins = pnat` to `/etc/bluetooth/main.conf` post setup install to ensure proper BT pairing.

On client, edit `tinderbox.py` to match your GPIO mapping or OLED screen type before running.

On demo server, edit `demoLedServer.py` to match your LED GPIO mapping before running.
