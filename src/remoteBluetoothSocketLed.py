import RPi.GPIO as GPIO
import time
import bluetooth

led_gpio = [22, 27, 17, 4]
server_port = 2
            
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

for led in led_gpio:
    GPIO.setup(led, GPIO.OUT)
    GPIO.output(led, False)

server_sock.bind(("", server_port))
server_sock.listen(1)

client_sock,address = server_sock.accept()
print("Accepted connection from {}".format(address))
current_tone = 0
try:
    while True:
        raw_command = client_sock.recv(1024)
        try:
            command_num = int(raw_command)
            print("Received \"{}\" from {}".format(command_num, address[0]))
            if command_num == 0:
                exit()
            if command_num >= 1 and command_num <= 4 and current_tone != command_num:
                if current_tone != 0:
                    GPIO.output(led_gpio[current_tone - 1], False)
                GPIO.output(led_gpio[command_num - 1], True)
                current_tone = command_num
        except:
            print("Unexpected Error: ", sys_exc_info()[0])
            server_sock.close()
            client_sock.close()
            if current_tone != 0:
                GPIO.output(led_gpio[current_tone - 1], False)
            GPIO.cleanup()
finally:
    server_sock.close()
    client_sock.close()
    if current_tone != 0:
        GPIO.output(led_gpio[current_tone - 1], False)
    GPIO.cleanup()
