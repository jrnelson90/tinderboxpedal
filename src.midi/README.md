# USB MIDI footswitch for Positive Grid Spark

Supported / tested USB MIDI footswitches: 

 - Icon G-Board

## Quick start

You will need:

 - a supported footswitch
 - a Raspberry Pi 4 (2Gb version should work, 4Gb version was used). It gets hot, invest a few $$s for good passive cooling enclosure. You will need a power supply as well, the official one may be the safest way
 - Ubuntu 20.04 LTS from https://ubuntu.com/download/raspberry-pi installed on a SD card

If attached to USB3 (green) ports, Pi 3 boots with MIDI controller attached. An example service definition is in the repo, you may want to adjust paths in it
before installing / enabling it.


Following packages should be installed:

    sudo apt install pi-bluetooth
    sudo apt install python3-bluez
    sudo apt install python3-rtmidi

and restart the Pi.

Make sure that no other Bluetooth device is connected to your Spark, and start the script with

    python3 ./midibox.py

You should see messages about MIDI device discovered.

Push the leftmost button on the to row to connect / disconnect the pedal from amplifier.

The bottom row of the footswitch is changing amp presets when connected.

