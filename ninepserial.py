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


class MicroPythonStdioNeoPixel:
    def __init__(self):
        if sys.implementation.name != "micropython":
            raise OSError("This is not micropython")
        import machine
        self.neopixel = machine.Neopixel(27, 1)
        self.rainbow = [machine.Neopixel.BLACK, machine.Neopixel.BLUE,
                        machine.Neopixel.RED, machine.Neopixel.MAGENTA,
                        machine.Neopixel.GREEN, machine.Neopixel.CYAN,
                        machine.Neopixel.YELLOW, machine.Neopixel.WHITE]
        self.pointer = 0

    def next(self):
        self.pointer = (self.pointer + 1) % len(self.rainbow)
        self.neopixel.set(0, self.rainbow[self.pointer])

    def read(self, n=-1):
        self.next()
        return sys.stdin.buffer.read(n)

    def write(self, s):
        self.next()
        import machine
        return machine.stdout_put(s)


def start():
    if sys.implementation.name == "micropython":
        import micropython
        # ignore break
        micropython.kbd_intr(-1)
        fd = MicroPythonStdioNeoPixel()
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
    start()
