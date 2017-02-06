#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import serial

READ_TIMOUT = 0.2

def usage():
    print('Usage: load.py on|off')

op = None
if len(sys.argv) == 2:
    op = sys.argv[1]
if op is None:
    if op != "on" and op != 'off':
        usage()
        sys.exit(1)

if op == 'on':
    print('Turning load on...')
    command = b':8ABED0001B4\n'
else:
    print('Turning load off...')
    command = b':8ABED0000B5\n'

ser = serial.Serial(port='/dev/ttyAMA0',
                    baudrate=19200,
                    timeout=READ_TIMOUT)

ser.write(command)
ser.close()

