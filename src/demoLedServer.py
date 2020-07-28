import RPi.GPIO as GPIO
import time
import bluetooth
import subprocess

led_gpio = [22, 27, 17, 4]
server_port = 2

# these are based on the wireshark captures when selecting presets via the app, 
# the correct commands probably involve reading state, then changing individual bytes before send to amp
cmdPreset1 = "01fe000053fe1a000000000000000000f00124000138000000f779"
cmdPreset2 = "01fe000053fe1a000000000000000000f00123010138000001f779"
cmdPreset3 = "01fe000053fe1a000000000000000000f00125020138000002f779"
cmdPreset4 = "01fe000053fe1a000000000000000000f00120030138000003f779"
toneCommands= [cmdPreset1, cmdPreset2, cmdPreset3, cmdPreset4]

subprocess.call(["sudo", "hciconfig", "hci0", "piscan"])

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

for led in led_gpio:
    GPIO.setup(led, GPIO.OUT)
    GPIO.output(led, False)

try:
    while True:
        server_sock.bind(("", server_port))
        server_sock.listen(1)

        print("Listening on BT port {}".format(server_port))

        client_sock,address = server_sock.accept()
        print("Accepted connection from {}".format(address))
        current_tone = 0
        connected = True
        while connected:
            raw_command = None
            try:
                raw_command = client_sock.recv(1024)
            except:
                print("Unexpected Error: ", sys_exc_info()[0])
                server_sock.close()
                client_sock.close()
                if current_tone != 0:
                    GPIO.output(led_gpio[current_tone - 1], False)
                connected = False

            if raw_command != None:        
                command_hex = raw_command.hex()
                command_num = toneCommands.index(command_hex) + 1
                print("Received \"{}\" from {}".format(command_num, address[0]))
                if command_num == 0:
                    exit()
                if command_num >= 1 and command_num <= 4 and current_tone != command_num:
                    if current_tone != 0:
                        GPIO.output(led_gpio[current_tone - 1], False)
                    GPIO.output(led_gpio[command_num - 1], True)
                    current_tone = command_num
finally:
    server_sock.close()
    client_sock.close()
    if current_tone != 0:
        GPIO.output(led_gpio[current_tone - 1], False)
    GPIO.cleanup()
