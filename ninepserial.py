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
