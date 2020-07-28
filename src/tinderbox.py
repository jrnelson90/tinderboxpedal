import time
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

# These are based on Wireshark BT packet captures when selecting presets via the app,
# the correct commands probably involve reading state, then changing individual bytes before send to amp
cmdPreset1 = "01fe000053fe1a000000000000000000f00124000138000000f779"
cmdPreset2 = "01fe000053fe1a000000000000000000f00123010138000001f779"
cmdPreset3 = "01fe000053fe1a000000000000000000f00125020138000002f779"
cmdPreset4 = "01fe000053fe1a000000000000000000f00120030138000003f779"
toneCommands = [cmdPreset1, cmdPreset2, cmdPreset3, cmdPreset4]

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
width = 128
height = 64
padding = -2
top = padding
bottom = height - padding

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
        draw.rectangle((0, 0, width, height), outline=0, fill=0)


def show_startup_splash():
    print("Showing Startup Splash")
    with canvas(device) as draw:
        draw.text((0, 20), "TinderBox", font=logo_font, fill=1)
        draw.text((56, 50), "v0.3", fill=1)
    time.sleep(3)


def find_bt_devices():
    while True:
        with canvas(device) as draw:
            draw.text((20, 16), "Scanning For\nBT Devices", font=medium_font, fill=1, align="center")
        print("Scanning For BT Devices")
        devices = bluetooth.discover_devices(duration=10)
        if devices:
            response = bt_device_selection(devices)
            if response != "rescan":
                return response
            else:
                print("Rescanning for BT Devices")
        else:
            print("No BT Devices Found")
            with canvas(device) as draw:
                draw.text((0, 20), "Re-scan BT Devices?", font=medium_font, fill=1, align="center")
            if not wait_for_yn_response():
                exit(0)


def bt_device_selection(devices):
    selection_mac = ""
    response = False
    num_of_devices = len(devices)
    selected_device = 0
    first_loop = True
    menu_top = 0
    menu_bottom = 3
    print("Found {} BT Devices".format(num_of_devices))
    for d in devices:
        print(d)
    while not response:
        nav_press = False
        if GPIO.input(BUTTON_1) and selected_device != 0:
            print("Device Selection Nav Up Pressed - Button 1")
            selected_device -= 1
            nav_press = True
            if menu_top != 0 and menu_top > selected_device:
                menu_bottom -= 1
                menu_top -= 1
        if GPIO.input(BUTTON_3) and selected_device != (num_of_devices - 1):
            print("Device Selection Nav Down Pressed - Button 3")
            selected_device += 1
            nav_press = True
            if menu_bottom != num_of_devices - 1 and menu_bottom < selected_device:
                menu_bottom += 1
                menu_top += 1
        if GPIO.input(BUTTON_4):
            print("Device Selection Confirm Pressed - Button 4")
            selection_mac = devices[selected_device]
            response = True
        if GPIO.input(BUTTON_2):
            print("Device Selection Rescan Pressed - Button 2")
            selection_mac = "rescan"
            response = True
        if nav_press or first_loop:
            if first_loop:
                first_loop = False
            display_bt_devices_found(devices, selected_device, menu_top, menu_bottom)
            # Debounce pause
            time.sleep(.1)
    return selection_mac


def display_bt_devices_found(devices, selected_device, menu_top, menu_bottom):
    num_of_devices = len(devices)
    list_space = 12
    with canvas(device) as draw:
        draw.text((0, 0), "  Found {} Devices:".format(num_of_devices), fill=1)
        for i, d in enumerate(devices[menu_top:(menu_bottom + 1)], start=menu_top):
            if i == selected_device:
                draw.text((0, list_space), "->{}".format(d), fill=1)
            else:
                draw.text((0, list_space), "  {}".format(d), fill=1)
            list_space += 12


def wait_for_yn_response():
    response = False
    press = ""
    while not response:
        if GPIO.input(BUTTON_4):
            press = "yes"
        if GPIO.input(BUTTON_3):
            press = "no"
        if press != "":
            response = True
    return press == "yes"


def connect_to_bt_device(server_addr):
    print("Connecting to {}".format(server_addr))
    with canvas(device) as draw:
        draw.text((4, 8), "Connecting to\n{}".format(server_addr), font=medium_font, fill=1, align="center")
    try:
        client_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        client_socket.connect((server_addr, server_port))
        print("Connecting to {} succeeded".format(server_addr))
        with canvas(device) as draw:
            draw.text((4, 8), "Connecting to\n{}\nSucceeded".format(server_addr), font=medium_font, fill=1,
                      align="center")
        time.sleep(3)
        return client_socket
    except OSError as e:
        print(e)
        print("Connecting to {} failed".format(server_addr))
        with canvas(device) as draw:
            draw.text((4, 8), "Connecting to\n{}\nFailed".format(server_addr), font=medium_font, fill=1,
                      align="center")
        time.sleep(3)
        return None


def update_slot_on_screen(selected_slot):
    with canvas(device) as draw:
        draw.text((48, top + 8), "{}".format(selected_slot), font=large_font, fill=1)


def tone_control_loop(client_socket):
    with canvas(device) as draw:
        draw.text((24, 16), "Select Initial\nTone Slot", font=medium_font, align="center", fill=1)
    selected_slot = 0
    multi_button_press = 0
    disconnect = False
    while not disconnect:
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
            msg = bytes.fromhex(toneCommands[selected_slot - 1])
            try:
                client_socket.send(msg)
                # Update screen with new selection
                update_slot_on_screen(selected_slot)
                print("Sent \"{}\" to server".format(selected_slot))
                multi_button_press = 0
                # Debounce pause
                time.sleep(.1)
            except OSError as e:
                print(e)
                disconnect = True
        elif new_press.count(True) == 2:
            if multi_button_press >= 5:
                client_socket.close()
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

    # TODO: refactor this socket to be passed or global
    # client_sock.close()

    exit(0)


if __name__ == '__main__':
    # Tell Python to run the handler() function when SIGINT is recieved
    signal(SIGINT, handler)

show_startup_splash()

client_sock = None
try:
    while True:
        server_address = find_bt_devices()
        client_sock = connect_to_bt_device(server_address)
        if client_sock is not None:
            tone_control_loop(client_sock)
finally:
    if client_sock is not None:
        client_sock.close()
