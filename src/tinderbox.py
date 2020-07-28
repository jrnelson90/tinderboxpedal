import bluetooth
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.core.sprite_system import framerate_regulator
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont, ImageSequence
import RPi.GPIO as GPIO
from signal import signal, SIGINT
from sys import exit
import time

VERSION = "0.3"
# Set Connection Port Default
SERVER_PORT = 2

# Hex Code Spark Tone Commands
TONE_1 = "01fe000053fe1a000000000000000000f00124000138000000f779"
TONE_2 = "01fe000053fe1a000000000000000000f00123010138000001f779"
TONE_3 = "01fe000053fe1a000000000000000000f00125020138000002f779"
TONE_4 = "01fe000053fe1a000000000000000000f00120030138000003f779"
TONE_CMD_LIST = [TONE_1, TONE_2, TONE_3, TONE_4]

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

# Load fonts
font = ImageFont.load_default()
medium_font = ImageFont.truetype('./roboto/Roboto-Regular.ttf', 14)
logo_font = ImageFont.truetype('./Market_Deco.ttf', 24)
large_font = ImageFont.truetype('./Market_Deco.ttf', 56)
print("Font Setup Complete")

# Setup 128x64 I2C OLED Display:
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
serial = i2c(port=1, address=0x3c)
oled_screen = ssd1306(serial, SCREEN_WIDTH, SCREEN_HEIGHT)
print("I2C OLED Setup Complete")


# Define script functions
def blank_screen():
    print("Blanking OLED Screen")
    with canvas(oled_screen) as draw:
        draw.rectangle((0, 0, SCREEN_WIDTH, SCREEN_HEIGHT), outline=0, fill=0)


def center_text(msg, msg_font):
    image = Image.new("RGBA", (SCREEN_WIDTH, SCREEN_HEIGHT), "black")
    draw = ImageDraw.Draw(image)
    text_w, text_h = draw.textsize(msg, font=msg_font)
    return (SCREEN_WIDTH - text_w) / 2, (SCREEN_HEIGHT - text_h) / 2


def show_startup_splash():
    print("Showing Startup Splash")
    regulator = framerate_regulator(fps=24)
    flame_animation = Image.open("./flame.gif")
    size = oled_screen.size

    for frame in ImageSequence.Iterator(flame_animation):
        with regulator:
            background = Image.new("RGB", oled_screen.size, "black")
            background.paste(frame.resize(size, resample=Image.LANCZOS), (0, 0))
            oled_screen.display(background.convert(oled_screen.mode))

    with canvas(oled_screen) as draw:
        name_msg = "TinderBox"
        version_msg = "v{}".format(VERSION)
        draw.text(center_text(name_msg, logo_font), name_msg, font=logo_font, fill=1)
        draw.text((center_text(version_msg, font)[0], center_text(name_msg, logo_font)[1] + 28), version_msg, fill=1)
    time.sleep(3)


def find_bt_devices():
    while True:
        with canvas(oled_screen) as draw:
            scan_msg = "Scanning For\nBT Devices"
            draw.text(center_text(scan_msg, medium_font), scan_msg, font=medium_font, fill=1, align="center")
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
            with canvas(oled_screen) as draw:
                rescan_msg = "Re-scan BT Devices?"
                draw.text(center_text(rescan_msg, medium_font), rescan_msg, font=medium_font, fill=1, align="center")
            if not wait_for_yn_response():
                exit(0)


def bt_device_selection(devices):
    selection_mac = ""
    response = False
    first_loop = True
    num_of_devices = len(devices)
    selected_device = 0
    menu_top = 0
    menu_bottom = 3
    print("Found {} BT Devices".format(num_of_devices))
    for d in devices:
        print(d)
    while not response:
        nav_press = False
        if GPIO.input(BUTTON_1) and selected_device != 0:
            print("Device Selection Button 1 Pressed - Device Menu Nav Up")
            selected_device -= 1
            nav_press = True
            if menu_top != 0 and menu_top > selected_device:
                menu_bottom -= 1
                menu_top -= 1
        if GPIO.input(BUTTON_3) and selected_device != (num_of_devices - 1):
            print("Device Selection Button 3 Pressed - Device Menu Nav Down")
            selected_device += 1
            nav_press = True
            if menu_bottom != num_of_devices - 1 and menu_bottom < selected_device:
                menu_bottom += 1
                menu_top += 1
        if GPIO.input(BUTTON_4):
            print("Device Selection Button 4 Pressed - Device Menu Confirm Selection")
            selection_mac = devices[selected_device]
            response = True
        if GPIO.input(BUTTON_2):
            print("Device Selection Button 2 Pressed - Device Menu Rescan Devices")
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
    with canvas(oled_screen) as draw:
        found_msg = "Found {} Devices".format(num_of_devices)
        draw.text((center_text(found_msg, font)[0], 0), found_msg, fill=1)
        for i, d in enumerate(devices[menu_top:(menu_bottom + 1)], start=menu_top):
            if i == selected_device:
                selected_msg = "->{}".format(d)
                draw.text((center_text(selected_msg, font)[0], list_space), selected_msg, fill=1)
            else:
                unselected_msg = "  {}".format(d)
                draw.text((center_text(unselected_msg, font)[0], list_space), unselected_msg, fill=1)
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
    with canvas(oled_screen) as draw:
        connecting_msg = "Connecting to\n{}".format(server_addr)
        draw.text(center_text(connecting_msg, medium_font), connecting_msg, font=medium_font, fill=1, align="center")
    try:
        client_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        client_socket.connect((server_addr, SERVER_PORT))
        print("Connecting to {} succeeded".format(server_addr))
        with canvas(oled_screen) as draw:
            connected_msg = "Connecting to\n{}\nSucceeded".format(server_addr)
            draw.text(center_text(connected_msg, medium_font), connected_msg, font=medium_font, fill=1, align="center")
        time.sleep(3)
        return client_socket
    except OSError as e:
        print(e)
        print("Connecting to {} failed".format(server_addr))
        with canvas(oled_screen) as draw:
            connect_failed_msg = "Connecting to\n{}\nFailed".format(server_addr)
            draw.text(center_text(connect_failed_msg, medium_font), connect_failed_msg, font=medium_font, fill=1,
                      align="center")
        time.sleep(3)
        return None


def update_slot_on_screen(selected_slot):
    with canvas(oled_screen) as draw:
        slot_msg = "{}".format(selected_slot)
        draw.text(center_text(slot_msg, large_font), slot_msg, font=large_font, fill=1)


def tone_control_loop(client_socket):
    with canvas(oled_screen) as draw:
        select_slot_msg = "Select Initial\nTone Slot"
        draw.text(center_text(select_slot_msg, medium_font), select_slot_msg, font=medium_font, align="center", fill=1)
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
            msg = bytes.fromhex(TONE_CMD_LIST[selected_slot - 1])
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
            if 5 > multi_button_press >= 2.5:
                with canvas(oled_screen) as draw:
                    disconnecting_msg = "Disconnecting from\nBT Device..."
                    draw.text(center_text(disconnecting_msg, medium_font), disconnecting_msg, font=medium_font, fill=1,
                              align="center")
            if multi_button_press >= 5:
                client_socket.close()
                disconnect = True
                with canvas(oled_screen) as draw:
                    disconnected_msg = "Disconnected from\nBT Device"
                    draw.text(center_text(disconnected_msg, medium_font), disconnected_msg, font=medium_font, fill=1,
                              align="center")
                print("Disconnected from server")
                time.sleep(3)
            else:
                multi_button_press += 0.1
                time.sleep(.1)
        elif new_press.count(True) == 0:
            multi_button_press = 0
            if selected_slot != 0:
                update_slot_on_screen(selected_slot)


# noinspection PyUnusedLocal
def keyboard_exit_handler(signal_received, frame):
    # Hard exit cleanup
    blank_screen()
    GPIO.cleanup()
    print('\nSIGINT or CTRL-C detected. Exiting TinderBox.')

    # TODO: refactor this socket to be passed or global
    # client_sock.close()

    exit(0)


# Start "main" logic
if __name__ == '__main__':
    # Tell Python to run the handler() function when Ctrl+C (SIGINT) is recieved
    signal(SIGINT, keyboard_exit_handler)

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
