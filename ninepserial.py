# /usr/bin/python3
import sys, os, io
import random
import time

from peanein.server import Server
from peanein.base import FileSystemDriver, Stat, Qid

from noddy import Noddy


class StdioWrapper:
    def read(self, n=-1):
        return os.read(0, n)

    def write(self, s):
        return os.write(1, s)


class MicroPythonStdio:
    def __init__(self):
        if sys.implementation.name != "micropython":
            raise OSError("This is not micropython")

    def read(self, n=-1):
        return sys.stdin.buffer.read(n)

    def write(self, s):
        import machine
        return machine.stdout_put(s)


class MicroPythonUart:
    def __init__(self):
        if sys.implementation.name != "micropython":
            raise OSError("This is not micropython")
        from machine import Pin, UART

        self.uart = UART(1, tx=1, rx=3, baudrate=115200)
        key_1 = Pin(27, Pin.IN, Pin.PULL_UP)
        key_2 = Pin(25, Pin.IN, Pin.PULL_UP)
        key_3 = Pin(32, Pin.IN, Pin.PULL_UP)

        if not (key_1.value() == 1 and key_2.value() == 1 and key_3.value() == 1):
            raise Exception("UART issues.")

    def read(self, n=32):  # We never return None/EOF
        block = bytearray(n)
        while len(block) == n:
            if self.uart.any() > 0:
                c = self.uart.read(1)
                block[len(block)] = c
            else:  # this is a terrible idea.
                time.sleep(0.001)
        return block

    def write(self, s):
        n = self.uart.write(s)
        return n


def run():
    if sys.implementation.name == "micropython":
        import micropython
        micropython.kbd_intr(-1)

        fd = MicroPythonStdio()
        fd.write("\n\nREADY")

    else:
        fd = StdioWrapper()

    srv = Server(fd, Noddy())

    while True:
        try:
            srv.next()
        except Exception as e:
            fd.write("\n\n\n+++ BAILING: %s\n\n\n" % e)
            if sys.implementation.name == "micropython":
                import machine
                fd.write("\n\n\n\n* RESETTING *\n\n\n")
                machine.reset()
            break


# print("imported ninepserial...")
# print(__name__)
# Main
if __name__ == 'ninepserial':
    run()
