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


# NOTE: this does not work under unix micropython because sys.stdin is a TextIOWrapper

class MicroPythonStdioWrapper:
    def __init__(self):
        if sys.implementation.name != "micropython":
            raise OSError("This is not micropython")

    def read(self, n=32):
        data = sys.stdin.read(n)
        return data

    def write(self, s):
        n = sys.stdout.write(s)
        return n


def run():
    if sys.implementation.name == "micropython":
        import micropython

        micropython.kbd_intr(-1)
        fd = MicroPythonStdioWrapper()
    else:
        fd = StdioWrapper()

    srv = Server(fd, Noddy())

    while True:
        try:
            srv.next()
        except Exception as e:
            if sys.implementation.name == "micropython":
                # we skip until we find a valid message?
                pass
            else:
                sys.stderr.write("bailing - %s\n\n\n" % e)
            break


# Main
if __name__ == '__main__':
    run()
