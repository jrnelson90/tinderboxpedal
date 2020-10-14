import logging
import time

import bluetooth
import rtmidi
from rtmidi.midiconstants import NOTE_OFF, NOTE_ON

VERSION = '0.3-midi'
# Set Connection Port Default
SERVER_PORT = 2

# Hex Code Spark Tone Commands
TONE_1   = '01 38 00 00 00'
TONE_2   = '01 38 00 00 01'
TONE_3   = '01 38 00 00 02'
TONE_4   = '01 38 00 00 03'
TONE_CMD_LIST = [TONE_1, TONE_2, TONE_3, TONE_4]

CONFIG_1 = '02 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'
CONFIG_2 = '02 01 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'
CONFIG_3 = '02 01 00 00 02 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'
CONFIG_4 = '02 01 00 00 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00'
CONFIG_CMD_LIST = [CONFIG_1, CONFIG_2, CONFIG_3, CONFIG_4]

HW_NAME  = '02 11'
HW_ID    = '02 23'

class BluetoothInterface(object):
    def __init__(self):
        self.spark_mac = None
        self.bt_socket = None
        self.scan()
        self.connect()

    def scan(self, duration=10):
        devices = bluetooth.discover_devices(duration, lookup_names=True)
        for addr, name in devices:
            if str(name).startswith('Spark'):
                logging.debug('Found {0} MAC {1}'.format(name, addr))
                self.spark_mac = addr

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

    def receive(self) -> str:
        last_byte = 0
        message = ''
        while  last_byte != 0xf7:
            data = self.bt_socket.recv(1024)
            if not data:
                return message
            last_byte = list(data)[-1]
            # first 0x10 bytes are from known header, igonre them
            if message == '':
                # Also remove 'f0 01 xx xx' header from the message
                logging.debug('Received {}'.format(bytes.hex(data)[0x14*2:]))
                message += bytes.hex(data)[0x14*2:]
            else:
                logging.debug('Received {}'.format(bytes.hex(data)[0x10*2:]))
                message += bytes.hex(data)[0x10*2:]
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
        slot = None
        msg = self.indev.get_message()
        if msg:
            message, deltatime = msg
            logging.debug('MIDI IN: %r' % (message))
            if message[0] == 144 and message[2] == 127:
                slot = message[1] - 91
                if (slot >=0) and (slot <=3):
                    logging.debug('Changing to slot {0}'.format(slot))
                    return slot
                if message[1] == 86:
                    slot = 4
                if message[1] == 95:
                    slot = 5
                if message[1] == 48:
                    slot = 6
                if message[1] == 49:
                    slot = 7
                if slot is not None:
                    logging.debug('Non-slot button {} pressed'.format(slot))
                    return slot
        return None
        return None

    def set_slot(self, slot: int):
        logging.debug('Changed to slot {0}'.format(slot))
        for button in range(0,4):
            if button == slot:
                msg = [ NOTE_ON, 91+button , 127 ]
            else:
                msg = [ NOTE_ON, 91+button , 0 ]
            self.outdev.send_message(msg)
        return None


def tone_control_loop(midi: MidiInterface, bt: BluetoothInterface) -> None:
    selected_slot = 0
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
    while True:
        selected_slot = midi.get_button()
        if selected_slot is not None and selected_slot in range(0, 4):
            bt.send(TONE_CMD_LIST[selected_slot])
            midi.set_slot(selected_slot)
            bt.receive()
        time.sleep(0.1)


def midibox():
    logging.basicConfig(level=logging.DEBUG)
    midi = MidiInterface()
    bt = BluetoothInterface()
    tone_control_loop(midi, bt)


# Start 'main' logic
if __name__ == '__main__':
    midibox()
