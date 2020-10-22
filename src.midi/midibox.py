import logging
import time

import bluetooth
import rtmidi
from rtmidi.midiconstants import NOTE_OFF, NOTE_ON

VERSION = '0.3-midi'
# Set Connection Port Default
SERVER_PORT = 2

# Hex Code Spark Tone Commands
TONE_1   = '01 38 00 00 00' # SET PRESET INT 0x## 0x##
TONE_2   = '01 38 00 00 01'
TONE_3   = '01 38 00 00 02'
TONE_4   = '01 38 00 00 03'
TONE_CMD_LIST = [TONE_1, TONE_2, TONE_3, TONE_4]

CONFIG_1 = '02 01 00 00 00' # GET CONFIG INT 0x## 0x##
CONFIG_2 = '02 01 00 00 01'
CONFIG_3 = '02 01 00 00 02'
CONFIG_4 = '02 01 00 00 03'
CONFIG_CMD_LIST = [CONFIG_1, CONFIG_2, CONFIG_3, CONFIG_4]

HW_NAME  = '02 11' # GET NAME
HW_ID    = '02 23' # GET ID
CURRENT_CONFIG = '02 10' # GET CURRENT_PRESET

class BluetoothInterface(object):
    def __init__(self):
        self.spark_mac = None
        self.bt_socket = None

    def scan(self, duration=10):
        devices = bluetooth.discover_devices(duration, lookup_names=True)
        for addr, name in devices:
            if str(name).startswith('Spark'):
                logging.debug('Found {0} MAC {1}'.format(name, addr))
                self.spark_mac = addr
                return True
        return False

    def disconnect(self):
        try:
            self.bt_socket.close()
        except bluetooth.btcommon.BluetoothError:
            pass

    def connect(self):
        self.bt_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.bt_socket.connect((self.spark_mac, SERVER_PORT))

    def send_raw(self, command: str):
        command = str(command).replace(' ','')
        logging.debug('Sending {0}'.format(command))
        msg = bytes.fromhex(command)
        self.bt_socket.send(msg)

    def send(self, command: str):
        command = str(command).replace(' ','')
        logging.debug('Command {0}'.format(command))
        prefix   = '01 fe 00 00 53 fe'.replace(' ','')
        suffix1  = '00 00 00 00 00 00 00 00 00'.replace(' ','')
        suffix2  = 'f0 01'.replace(' ','')
        fake_seq = '01 01'.replace(' ','')
        suffix   = 'f7'.replace(' ','')
        command_len = len(prefix)/2 +                     1 + len(suffix1)/2 + len(suffix2)/2 + len(fake_seq)/2 + len(command)/2 + len(suffix)/2
        command_len = int(command_len)
        bt_command =      prefix    + ('%02x' % command_len) +     suffix1    +     suffix2    +     fake_seq    +     command    +     suffix 
        msg = bytes.fromhex(bt_command)
        self.bt_socket.send(msg)

    def receive(self):
        last_message = False
        message = []
        while not last_message:
            data = self.bt_socket.recv(1024)
            if not data:
                return message
            last_message = (list(data)[-1] == 0xf7) and (len(data) < 0x6a) 
            logging.debug('Received {}'.format(bytes.hex(data)))
            message.append(data)
        return message


class NoMidiDeviceException(Exception):
    """Exception accessing MIDI device."""


class MidiInterface(object):
    def __init__(self):
        self.midiin: rtmidi.MidiIn = None
        self.indev = None
        self.find_midi_in()
        self.midiout: rtmidi.MidiOut = None
        self.outdev = None
        self.find_midi_out()

    def find_midi_in(self):
        if self.midiin is None:
            self.midiin = rtmidi.MidiIn()
        if self.midiin is None:
            raise NoMidiDeviceException
        num_ports = self.midiin.get_port_count()
        for port in range(0, num_ports):
            if str(self.midiin.get_port_name(port)).startswith('iCON G_Boar'):
                logging.debug('MIDI IN: {0}'.format(self.midiin.get_port_name(port)))
                self.indev = self.midiin.open_port(port)
        if self.indev is None:
            raise NoMidiDeviceException

    def find_midi_out(self):
        if self.midiout is None:
            self.midiout = rtmidi.MidiOut()
        if self.midiout is None:
            raise NoMidiDeviceException
        num_ports = self.midiout.get_port_count()
        for port in range(0, num_ports):
            if str(self.midiout.get_port_name(port)).startswith('iCON G_Boar'):
                logging.debug('MIDI OUT: {0}'.format(self.midiout.get_port_name(port)))
                self.outdev = self.midiout.open_port(port)
        if self.outdev is None:
            raise NoMidiDeviceException

    def get_button(self):
        """ Get a MIDI message, convert to button (0-7), top row (0-3) to select preset
        Top row:
        DEBUG:root:[144, 91, 0]
        DEBUG:root:[144, 91, 127]
        DEBUG:root:[144, 92, 0]
        DEBUG:root:[144, 92, 127]
        DEBUG:root:[144, 93, 0]
        DEBUG:root:[144, 93, 127]
        DEBUG:root:[144, 94, 0]
        DEBUG:root:[144, 94, 127]
        Bottom row:
        DEBUG:root:[144, 86, 127]
        DEBUG:root:[144, 86, 0]
        DEBUG:root:[144, 95, 127]
        DEBUG:root:[144, 95, 0]
        DEBUG:root:[144, 48, 127]
        DEBUG:root:[144, 48, 0]
        DEBUG:root:[144, 49, 127]
        DEBUG:root:[144, 49, 0]
        """
        button = None
        msg = self.indev.get_message()
        if msg:
            message, deltatime = msg
            logging.debug('MIDI IN: %r' % (message))
            if message[0] == 144 and message[2] == 127:
                button = message[1] - 91
                if (button >=0) and (button <=3):
                    logging.debug('Button {0}'.format(button))
                    return button
                if message[1] == 86:
                    button = 4
                if message[1] == 95:
                    button = 5
                if message[1] == 48:
                    button = 6
                if message[1] == 49:
                    button = 7
                if button is not None:
                    logging.debug('Button {}'.format(button))
                    return button
        return None


    def set_led(self, led: int, mode: bool):
        notes = [91,92,93,94,86,95,48,49]
        if led not in range(0,8):
            return None
        if mode:
            velocity = 127
        else:
            velocity = 0
        msg = [ NOTE_ON, notes[led], velocity]
        self.outdev.send_message(msg)
        return None


def reconnect(bt):
    logging.debug('Amp ID')
    bt.send(HW_NAME)
    bt.receive()
    logging.debug('Amp SN')
    bt.send(HW_ID)
    bt.receive()
    logging.debug('Amp Presets')
    for slot in range(0, 4):
        logging.debug('Preset {}'.format(slot))
        bt.send(CONFIG_CMD_LIST[slot])
        bt.receive()
    logging.debug('Current preset:')
    bt.send(CURRENT_CONFIG)
    messages = bt.receive()
    preset = None
    if len(messages) == 1:
        preset = int.from_bytes(messages[0][-3:-1], "big")
    return preset

# 0-based, buttons are 0..7
BUTTON_ONOFF = 0
BUTTON_PRESET0 = 4 

NUM_PRESETS = 4
NUM_BUTTONS = 8

def set_leds_midi_found(midi):
    for led in range(0, NUM_BUTTONS):
        midi.set_led(led, True)
    time.sleep(0.5)
    for led in range(0, NUM_BUTTONS):
        midi.set_led(led, False)
    time.sleep(0.5)
    for led in range(0, NUM_BUTTONS):
        midi.set_led(led, True)
    time.sleep(0.5)
    for led in range(0, NUM_BUTTONS):
        midi.set_led(led, False)

def set_leds_scan(midi):
    for led in range(BUTTON_PRESET0,BUTTON_PRESET0+NUM_PRESETS):
        midi.set_led(led, True)
    midi.set_led(BUTTON_ONOFF, False)

def set_leds_off(midi, spark_connected):
    for led in range(BUTTON_PRESET0,BUTTON_PRESET0+NUM_PRESETS):
        midi.set_led(led, False)
    midi.set_led(BUTTON_ONOFF, spark_connected)

def set_preset_led(midi, slot: int):
    logging.debug('Changed to slot {0}'.format(slot))
    for led in range(0, NUM_PRESETS):
        midi.set_led(BUTTON_PRESET0+led, (led == slot))
    return None

def tone_control_loop(midi: MidiInterface) -> None:
    set_leds_midi_found(midi)
    selected_slot = None
    bt = BluetoothInterface()
    spark_connected = False
    set_leds_off(midi, spark_connected)
    while True:
        button = midi.get_button()
        if button is None:
            time.sleep(0.1)
            continue
        if button == BUTTON_ONOFF:
            selected_slot = None
            if not spark_connected:
                logging.debug('scan')
                set_leds_scan(midi)
                if bt.scan():
                    logging.debug('connect')
                    bt.connect()
                    selected_slot = reconnect(bt)
                    spark_connected = True
            else:
                logging.debug('disconnect')
                bt.disconnect()
                spark_connected = False
            set_leds_off(midi, spark_connected)
            if selected_slot is not None:
                set_preset_led(midi, selected_slot)
        if spark_connected and button in range(BUTTON_PRESET0, BUTTON_PRESET0+NUM_PRESETS):
            selected_slot = button - BUTTON_PRESET0
            try:
                bt.send(TONE_CMD_LIST[selected_slot])
                set_preset_led(midi, selected_slot)
                bt.receive()
            except bluetooth.btcommon.BluetoothError as e:
                logging.info('BT connection lost')
                bt.disconnect()
                spark_connected = False
                set_leds_off(midi, spark_connected)
        time.sleep(0.1)


def midibox():
    logging.basicConfig(level=logging.DEBUG)
    midi = None
    while midi is None:
        try:
            midi = MidiInterface()
        except NoMidiDeviceException:
            logging.debug('No MIDI, sleep 10 seconds')
            time.sleep(10)
    logging.debug('Draining MIDI queue....')
    while midi.get_button() is not None:
        pass # drain MIDI messages
    tone_control_loop(midi)


# Start 'main' logic
if __name__ == '__main__':
    midibox()
