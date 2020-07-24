import time
import Adafruit_SSD1306
from PIL import Image
from PIL import ImageDraw
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

# Raspberry Pi pin configuration:
RST = None     # on the PiOLED this pin isnt used

# 128x64 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

# Initialize library.
disp.begin()

# Clear display.
disp.clear()
disp.display()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)

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

server_address = "DC:A6:32:AF:F3:1C"
server_port = 2
client_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
client_sock.connect((server_address, server_port))

try:
    while True:
        # Draw a black filled box to clear the image.
        draw.rectangle((0,0,width,height), outline=0, fill=0)
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
        
        # Write two lines of text.
        draw.text((x+8, top),     " TinderBox v0.1",  font=font, fill=255)
        draw.text((x+48, top+8),  "{}".format(selected_slot),  font=large_font, fill=255)

        # Display image.
        disp.image(image)
        disp.display()
        time.sleep(.1)
        
finally:
    client_sock.close()
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    disp.image(image)
    disp.display()
    GPIO.cleanup()
