import time
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont
import RPi.GPIO as GPIO
import bluetooth

# Set Connection and Tone Slot Defaults
selected_slot = 0;
server_port = 2;
server_address = ""
found_devices = False
connected = False

# these are based on the wireshark captures when selecting presets via the app, 
# the correct commands probably involve reading state, then changing individual bytes before send to amp
cmdPreset1 = "01fe000053fe1a000000000000000000f00124000138000000f779"
cmdPreset2 = "01fe000053fe1a000000000000000000f00123010138000001f779"
cmdPreset3 = "01fe000053fe1a000000000000000000f00125020138000002f779"
cmdPreset4 = "01fe000053fe1a000000000000000000f00120030138000003f779"
toneCommands= [cmdPreset1, cmdPreset2, cmdPreset3, cmdPreset4]

# Setup Button GPIO
BUTTON_1 = 20
BUTTON_2 = 21
BUTTON_3 = 19
BUTTON_4 = 26
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(BUTTON_2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(BUTTON_3, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(BUTTON_4, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height-padding

# Load fonts
font = ImageFont.load_default()
medium_font = ImageFont.truetype('./roboto/Roboto-Regular.ttf', 14)
logo_font = ImageFont.truetype('./Market_Deco.ttf', 24)
large_font = ImageFont.truetype('./Market_Deco.ttf', 56)

# Setup 128x64 I2C OLED Display:
width = 128
height = 64
serial = i2c(port=1, address=0x3c)
device = ssd1306(serial, width, height)

# Define script functions
def blank_screen():
    with canvas(device) as draw:
        draw.rectangle((0,0,width,height), outline=0, fill=0)

def showStartup():
    with canvas(device) as draw:
        draw.text((0, 20), "TinderBox", font=logo_font, fill=1)
        draw.text((56, 50), "v0.2", fill=1)
    time.sleep(3)

def findBTDevices():
    while connected != True:
        while found_devices != True:
            with canvas(device) as draw:
                draw.text((20,16), "Scanning For\nBT Devices", font=medium_font, fill=1, align="center")
            devices = bluetooth.discover_devices(duration=10)
            if devices:
                response = waitForBTDeviceSelection(devices)
                if response != "rescan":
                    server_address = response
                    found_devices = True
            else:
                print("No BT Devices Found")
                with canvas(device) as draw:
                    draw.text((0, 32), "Re-scan BT Devices?", fill=1)
                if waitForYNResponse() == False:
                    exit(0)

def waitForBTDeviceSelection(devices):
    selection_mac = ""
    response = False
    num_of_devices = len(devices)
    selected_device = 0
    first_loop = True
    while response != True:
        nav_press = False
        if GPIO.input(BUTTON_1) and selected_device != 0:
            selected_device -= 1
            nav_press = True
        if GPIO.input(BUTTON_3) and selected_device != (num_of_devices - 1):
            selected_device += 1
            nav_press = True
        if GPIO.input(BUTTON_4):
            selection_mac = devices[selected_device]
            response = True
        if GPIO.input(BUTTON_2):
            selection_mac = "rescan"
            response = True
        if nav_press == True or first_loop == True:
            if first_loop == True:
                first_loop = False
            displayBTDevicesFound(devices, selected_device)
            # Debounce pause
            time.sleep(.1)
    return selection_mac

def displayBTDevicesFound(devices, selected_device):
    num_of_devices = len(devices)
    list_space = 12
    with canvas(device) as draw:
        draw.text((0,0), "  Found {} Devices:".format(num_of_devices), fill=1)
        for i, d in enumerate(devices, start=0):
            print(d)
            if i == selected_device:
                draw.text((0, list_space), "->{}".format(d), fill=1)
            else:
                draw.text((0, list_space), "  {}".format(d), fill=1)
            list_space += 12

def waitForYNResponse():
    response = False
    press = ""
    while response != True:
        if GPIO.input(BUTTON_4):
            press = "yes"
        if GPIO.input(BUTTON_3):
            press = "no"
        if press != "":
            response = True
    return (press == "yes")

def connectToBTDevice():
    with canvas(device) as draw:
        draw.text((4,8), "Connecting to\n{}".format(server_address), font=medium_font, fill=1, align="center")
    try:
        client_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        client_sock.connect((server_address, server_port))
        connected = True
        with canvas(device) as draw:
            draw.text((4,8), "Connecting to\n{}\nSucceeded".format(server_address), font=medium_font, fill=1, align="center")
        time.sleep(3)
    except:
        print("Connecting to {} failed".format(server_address))
        with canvas(device) as draw:
            draw.text((4,8), "Connecting to\n{}\nFailed".format(server_address), font=medium_font, fill=1, align="center")
            found_devices = False
            server_address = ""
        time.sleep(3)

def updateSlotOnScreen():
    with canvas(device) as draw:
        draw.text((48, top+8), "{}".format(selected_slot), font=large_font, fill=1)

def toneControlLoop():
    with canvas(device) as draw:
        draw.text((4,8), "Select Initial\nTone Slot", font=medium_font, align="center")
    while True:
        new_press = 0
        if GPIO.input(BUTTON_1):
            new_press = 1
        if GPIO.input(BUTTON_2):
            new_press = 2
        if GPIO.input(BUTTON_3):
            new_press = 3
        if GPIO.input(BUTTON_4):
            new_press = 4
        if new_press != 0 and new_press != selected_slot:
            selected_slot = new_press
            msg = bytes.fromhex(toneCommands[new_press-1])
            client_sock.send(msg)
            # Update screen with new selection
            updateSlotOnScreen()
            # Debounce pause
            time.sleep(.1)

# Start "main" logic
showStartup()

findBTDevices()

connectToBTDevice()

try:
    toneControlLoop()
finally:
    client_sock.close()
    blank_screen()
    GPIO.cleanup()
