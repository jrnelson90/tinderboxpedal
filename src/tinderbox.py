import time
import traceback
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont
import RPi.GPIO as GPIO
import bluetooth
from signal import signal, SIGINT
from sys import exit

# Set Connection Port Default
server_port = 2

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
print("GPIO Setup Complete")

# First define some constants to allow easy resizing of shapes.
width =128
height = 64
padding = -2
top = padding
bottom = height-padding

# Load fonts
font = ImageFont.load_default()
medium_font = ImageFont.truetype('./roboto/Roboto-Regular.ttf', 14)
logo_font = ImageFont.truetype('./Market_Deco.ttf', 24)
large_font = ImageFont.truetype('./Market_Deco.ttf', 56)
print("Font Setup Complete")

# Setup 128x64 I2C OLED Display:
serial = i2c(port=1, address=0x3c)
device = ssd1306(serial, width, height)
print("I2C OLED Setup Complete")

# Define script functions
def blank_screen():
    print("Blanking OLED Screen")
    with canvas(device) as draw:
        draw.rectangle((0,0,width,height), outline=0, fill=0)

def showStartup():
    print("Showing Startup Splash")
    with canvas(device) as draw:
        draw.text((0, 20), "TinderBox", font=logo_font, fill=1)
        draw.text((56, 50), "v0.2", fill=1)
    time.sleep(3)

def findBTDevices():
    found_devices = False
    while found_devices != True:
        with canvas(device) as draw:
            draw.text((20,16), "Scanning For\nBT Devices", font=medium_font, fill=1, align="center")
        print("Scanning For BT Devices")
        devices = bluetooth.discover_devices(duration=10)
        if devices:
            response = waitForBTDeviceSelection(devices)
            if response != "rescan":
                found_devices = True
                return response
            else:
                print("Rescanning for BT Devices")
        else:
            print("No BT Devices Found")
            with canvas(device) as draw:
                draw.text((0, 20), "Re-scan BT Devices?", font=medium_font, fill=1, align="center")
            if waitForYNResponse() == False:
                exit(0)

def waitForBTDeviceSelection(devices):
    selection_mac = ""
    response = False
    num_of_devices = len(devices)
    selected_device = 0
    first_loop = True
    menu_top = 0
    menu_bottom = 3
    menu_size = 4
    print("Found {} BT Devices".format(num_of_devices))
    for d in devices:
        print(d)
    while response != True:
        nav_press = False
        if GPIO.input(BUTTON_1) and selected_device != 0:
            print("Device Selection Nav Up Pressed - Button 1")
            selected_device -= 1
            nav_press = True
            if menu_bottom != 0 and menu_bottom > selected_device:
                menu_bottom -= 1
                menu_top -= 1
        if GPIO.input(BUTTON_3) and selected_device != (num_of_devices - 1):
            print("Device Selection Nav Down Pressed - Button 3")
            selected_device += 1
            nav_press = True
            if menu_top != num_of_devices-1 and menu_top < selected_device:
                menu_bottom += 1
                menu_top +=1
        if GPIO.input(BUTTON_4):
            print("Device Selection Confirm Pressed - Button 4")
            selection_mac = devices[selected_device]
            response = True
        if GPIO.input(BUTTON_2):
            print("Device Selection Rescan Pressed - Button 2")
            selection_mac = "rescan"
            response = True
        if nav_press == True or first_loop == True:
            if first_loop == True:
                first_loop = False
            displayBTDevicesFound(devices, selected_device, menu_top, menu_bottom)
            # Debounce pause
            time.sleep(.1)
    return selection_mac

def displayBTDevicesFound(devices, selected_device, menu_top, menu_bottom):
    num_of_devices = len(devices)
    list_space = 12
    with canvas(device) as draw:
        draw.text((0,0), "  Found {} Devices:".format(num_of_devices), fill=1)
        for i, d in enumerate(devices[menu_bottom:(menu_top + 1)], start=0):
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

def connectToBTDevice(server_address):
    print("Connecting to {}".format(server_address))
    with canvas(device) as draw:
        draw.text((4,8), "Connecting to\n{}".format(server_address), font=medium_font, fill=1, align="center")
    try:
        client_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        client_sock.connect((server_address, server_port))
        print("Connecting to {} succeeded".format(server_address))
        with canvas(device) as draw:
            draw.text((4,8), "Connecting to\n{}\nSucceeded".format(server_address), font=medium_font, fill=1, align="center")
        time.sleep(3)
        return client_sock
    except:
        print("Connecting to {} failed".format(server_address))
        with canvas(device) as draw:
            draw.text((4,8), "Connecting to\n{}\nFailed".format(server_address), font=medium_font, fill=1, align="center")
        time.sleep(3)
        return None

def updateSlotOnScreen(selected_slot):
    with canvas(device) as draw:
        draw.text((48, top+8), "{}".format(selected_slot), font=large_font, fill=1)

def toneControlLoop(client_sock):
    with canvas(device) as draw:
        draw.text((24, 16), "Select Initial\nTone Slot", font=medium_font, align="center", fill=1)
    selected_slot = 0
    multi_button_press = 0
    disconnect = False
    while disconnect != True:
        new_press = [False, False, False, False]
        if GPIO.input(BUTTON_1):
            new_press[0] = True
        if GPIO.input(BUTTON_2):
            new_press[1] = True
        if GPIO.input(BUTTON_3):
            new_press[2] = True
        if GPIO.input(BUTTON_4):
            new_press[3] = True

        if new_press.count(True) == 1 and new_press.index(True) + 1 != selected_slot:
            selected_slot = new_press.index(True) + 1
            msg = bytes.fromhex(toneCommands[selected_slot-1])
            client_sock.send(msg)
            # Update screen with new selection
            updateSlotOnScreen(selected_slot)
            print("Sent \"{}\" to server".format(selected_slot))
            multi_button_press = 0
            # Debounce pause
            time.sleep(.1)
        elif new_press.count(True) == 2:
            if multi_button_press >= 5:
                client_sock.close()
                disconnect = True
                with canvas(device) as draw:
                    draw.text((8, 16), "Disconnected from\nBT Device", font=medium_font, fill=1, align="center")
                print("Disconnected from server")
                time.sleep(3)
            else:
                multi_button_press += 0.1
                time.sleep(.1)
        elif new_press.count(True) == 0:
            multi_button_press = 0

# Start "main" logic
def handler(signal_received, frame):
    # Handle any cleanup here
    blank_screen()
    GPIO.cleanup()
    print('SIGINT or CTRL-C detected. Exiting TinderBox.')
    
    #TODO: refactor this socket to be passed or global
    #client_sock.close()

    exit(0)

if __name__ == '__main__':
    # Tell Python to run the handler() function when SIGINT is recieved
    signal(SIGINT, handler)

showStartup()

try:
    while True:
        server_address = findBTDevices()
        client_sock = connectToBTDevice(server_address)
        if client_sock != None:
            toneControlLoop(client_sock)
finally:
    client_sock.close()

