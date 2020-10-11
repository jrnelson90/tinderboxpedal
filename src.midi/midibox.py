import logging
import time

import bluetooth
import rtmidi
from rtmidi.midiconstants import NOTE_OFF, NOTE_ON

VERSION = '0.3-midi'
# Set Connection Port Default
SERVER_PORT = 2

# Hex Code Spark Tone Commands
TONE_1 = '01fe000053fe1a000000000000000000f00124000138000000f7'
TONE_2 = '01fe000053fe1a000000000000000000f00123010138000001f7'
TONE_3 = '01fe000053fe1a000000000000000000f00125020138000002f7'
TONE_4 = '01fe000053fe1a000000000000000000f00120030138000003f7'
TONE_CMD_LIST = [TONE_1, TONE_2, TONE_3, TONE_4]


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

    def send(self, command: str):
        logging.debug('Sending {0}'.format(command))
        msg = bytes.fromhex(command)
        self.bt_socket.send(msg)

    def receive(self) -> str:
        # not implemeted yet
        return ''


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

    def get_slot(self):
        """ Get a MIDI message, convert to slot ID.
        Top row:
        DEBUG:root:[144, 91, 0]
        DEBUG:root:[144, 91, 127]
        DEBUG:root:[144, 92, 0]
        DEBUG:root:[144, 92, 127]
        DEBUG:root:[144, 93, 0]
        DEBUG:root:[144, 93, 127]
        DEBUG:root:[144, 94, 0]
        DEBUG:root:[144, 94, 127]
        """
        msg = self.indev.get_message()
        if msg:
            message, deltatime = msg
            logging.debug('MIDI IN: %r' % (message))
            if message[0] == 144 and message[2] == 127:
                slot = message[1] - 91
                if (slot >=0) and (slot <=3):
                    logging.debug('Changing to slot {0}'.format(slot))
                    return slot
        return None

    def set_slot(self, slot: int):
        logging.debug('Changed to slot {0}'.format(slot))
        for button in range(0,3):
            if button == slot:
                msg = [ NOTE_ON, 36+button , 127 ]
            else:
                msg = [ NOTE_ON, 36+button , 0 ]
            self.outdev.send_message(msg)
        return None


def tone_control_loop(midi: MidiInterface, bt: BluetoothInterface) -> None:
    selected_slot = 0
    while True:
        selected_slot = midi.get_slot()
        if selected_slot is not None:
            bt.send(TONE_CMD_LIST[selected_slot])
            midi.set_slot(selected_slot)
        time.sleep(0.1)


def midibox():
    logging.basicConfig(level=logging.DEBUG)
    midi = MidiInterface()
    bt = BluetoothInterface()
    tone_control_loop(midi, bt)


# Start 'main' logic
if __name__ == '__main__':
    midibox()
