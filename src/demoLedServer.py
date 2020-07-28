import bluetooth
import RPi.GPIO as GPIO
import subprocess

LED_GPIO_LIST = [22, 27, 17, 4]
SERVER_PORT = 2

# Hex Code Spark Tone Commands
TONE_1 = "01fe000053fe1a000000000000000000f00124000138000000f779"
TONE_2 = "01fe000053fe1a000000000000000000f00123010138000001f779"
TONE_3 = "01fe000053fe1a000000000000000000f00125020138000002f779"
TONE_4 = "01fe000053fe1a000000000000000000f00120030138000003f779"
TONE_CMD_LIST = [TONE_1, TONE_2, TONE_3, TONE_4]

subprocess.call(["sudo", "hciconfig", "hci0", "piscan"])

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

for led in LED_GPIO_LIST:
    GPIO.setup(led, GPIO.OUT)
    GPIO.output(led, False)

server_sock = None
client_sock = None
current_tone = 0

try:
    while True:
        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        server_sock.bind(("", SERVER_PORT))
        server_sock.listen(1)

        print("Listening on BT port {}".format(SERVER_PORT))

        client_sock, address = server_sock.accept()
        print("Accepted connection from {}".format(address))
        current_tone = 0
        connected = True
        while connected:
            raw_command = None
            try:
                raw_command = client_sock.recv(1024)
            except OSError as e:
                print("Unexpected Connection Error")
                server_sock.close()
                client_sock.close()
                if current_tone != 0:
                    GPIO.output(LED_GPIO_LIST[current_tone - 1], False)
                connected = False

            if raw_command is not None:
                command_hex = raw_command.hex()
                command_num = TONE_CMD_LIST.index(command_hex) + 1
                print("Received \"{}\" from {}".format(command_num, address[0]))
                if command_num == 0:
                    exit()
                if 1 <= command_num <= 4 and current_tone != command_num:
                    if current_tone != 0:
                        GPIO.output(LED_GPIO_LIST[current_tone - 1], False)
                    GPIO.output(LED_GPIO_LIST[command_num - 1], True)
                    current_tone = command_num
finally:
    if server_sock is not None:
        server_sock.close()
    if client_sock is not None:
        client_sock.close()
    if current_tone != 0:
        GPIO.output(LED_GPIO_LIST[current_tone - 1], False)
    GPIO.cleanup()
