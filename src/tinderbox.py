import time
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont
import subprocess
import RPi.GPIO as GPIO
import bluetooth

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(19, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(20, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Setup 128x64 I2C OLED Display:
width = 128
height = 64
serial = i2c(port=1, address=0x3c)
device = ssd1306(serial, width, height)

# Draw a black filled box to clear the image.
def blank_screen():
    with canvas(device) as draw:
        draw.rectangle((0,0,width,height), outline=0, fill=0)

with canvas(device) as draw:
    draw.text((40,20), "Connecting", fill=1)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# Load default font.
font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
large_font = ImageFont.truetype('./Market_Deco.ttf', 56)
selected_slot = 0;

def updateSlotOnScreen():
    with canvas(device) as draw:
        draw.text((x+8, top), "TinderBox v0.2", font=font, fill=1)
        draw.text((x+48, top+8), "{}".format(selected_slot), font=large_font, fill=1)

server_address = "DC:A6:32:AF:F3:1C"
server_port = 2
client_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
client_sock.connect((server_address, server_port))

updateSlotOnScreen()

try:
    while True:
        new_press = False
        if GPIO.input(26):
            selected_slot = 1
            new_press = True
        if GPIO.input(19):
            selected_slot = 2
            new_press = True
        if GPIO.input(21):
            selected_slot = 3
            new_press = True
        if GPIO.input(20):
            selected_slot = 4
            new_press = True
        if selected_slot != 0 and new_press == True:
            client_sock.send("{}".format(selected_slot))
            # Update screen with new selection
            updateSlotOnScreen()
            # Debounce pause
            time.sleep(.1)
finally:
    client_sock.close()
    blank_screen()
    GPIO.cleanup()
