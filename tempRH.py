import serial
import subprocess as sp
import json
import numpy as np
import time

class PowerMeterComm(object):
# Module for communicating with the power meter
    '''
    Simple optical power meter.

    Usage: Send plaintext commands, separated by newline/cr or semicolon.
           An eventual reply comes terminated with cr+lf.

    Important commands:

    *IDN?     Returns device identifier
    *RST      Resets device, outputs are 0V.
    RANGE <value>
              Chooses the shunt resistor index; <value> ranges from 1 to 5.
    VOLT?     Returns the voltage across the sense resistor.
    RAW?      Returns the voltage across the sense resistor in raw units.
    FLOW      starts acquisition every 1 ms and returns raw hex values
    STOP      resets the raw sample mode.
    ALLIN?    Returns all 8 input voltages and temperature.
    HELP      Print this help text.
    '''

    baudrate = 115200

    def __init__(self, port):
        self.serial = self._open_port(port)
        self.serial.write(b'*IDN?;')# flush io buffer
        print (self._serial_read()) #will read unknown command
        self.set_range(4)
        self.range = self.get_range
        self.data = self._read_cal_file()
        #self.set_range(4) #Sets bias resistor to 1k

    def _open_port(self, port):
        ser = serial.Serial(port, timeout=1)
        #ser.readline()
        #ser.timeout = 1 #causes problem with nexus 7
        return ser

    def close(self):
        self.serial.close()



    def _serial_write(self, string2):
        self.serial.write((string2+';').encode('UTF-8'))

    def _serial_read(self):
        msg_string = self.serial.readline().decode()
        # Remove any linefeeds etc
        msg_string = msg_string.rstrip()
        return msg_string

    def reset(self):
        self._serial_write('*RST')
        return self._serial_read()

    def get_intemp(self):
        #get instaneous temperature
        self._serial_write('ITEMP?')
        temp = self._serial_read()

        return temp

    def get_ntemp(self):
        self._serial_write('NTEMP?')
        temp = self._serial_read()

        return temp

    def get_temp(self):
        #get low pass filtered average temperature over 3.2 sec
        self._serial_write('TEMP?')
        temp = self._serial_read()
        return temp

    def on(self):
        #switch on thermistor
        self._serial_write('ON')

    def off(self):
        #switch on thermistor
        self._serial_write('OFF')
