#!/bin/sh

sudo apt update
sudo apt install python3 python3-dev python3-pip python3-smbus python3-pil i2c-tools libfreetype6-dev build-essential libjpeg-dev libtiff5 libopenjp2-7 libbluetooth-dev
pip3 install pybluez RPi.GPIO luma.oled
