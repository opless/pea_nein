# /usr/bin/python3
import sys, os, io
import random

from peanein.server import Server
from peanein.base import FileSystemDriver, Stat, Qid

from noddy import Noddy


class StdioWrapper:
    def read(self, n=-1):
        return os.read(0, n)

    def write(self, s):
        return os.write(1, s)


class MicroPythonUart:
    def __init__(self):
        if sys.implementation.name != "micropython":
            raise OSError("This is not micropython")
        import machine
        self.uart = machine.UART(0, 115200)

    def read(self, n=32):
        data = self.uart.read(n)
        return data

    def write(self, s):
        n = self.uart.write(s)
        return n


def run():
    if sys.implementation.name == "micropython":
        import micropython

        micropython.kbd_intr(-1)
        os.dupterm(None, 1)  # disable REPL on UART(0)

        fd = MicroPythonUart()
        fd.write("\n\nREADY")

    else:
        fd = StdioWrapper()

    srv = Server(fd, Noddy())

    while True:
        try:
            srv.next()
        except Exception as e:
            if sys.implementation.name == "micropython":
                sys.stdout.write("\n\n\nbailing - %s\n\n\n" % e)
                os.dupterm(machine.UART(0, 115200), 1)
            else:
                sys.stderr.write("bailing - %s\n\n\n" % e)
            break


# Main
if __name__ == '__main__':
    run()
