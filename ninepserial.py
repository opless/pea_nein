# /usr/bin/python3
import sys, os, io
import random

import peanein.framing
from peanein.server import Server
from peanein.base import FileSystemDriver, Stat, Qid

from noddy import Noddy


class StdioWrapper:
    def read(self, n=-1):
        return os.read(0, n)

    def write(self, s):
        return os.write(1, s)


def run():
    if sys.implementation.name == "micropython":
        import micropython

        micropython.kbd_intr(-1)
        print("\n\n\n\nBREAK DISABLED. 9P SERVICE NOW READY.\n\n\n\n")
        fd = peanein.framing.Framing(sys.stdin, sys.stdout)
    else:
        fd = StdioWrapper()

    srv = Server(fd, Noddy())

    while True:
        try:
            srv.next()
        except Exception as e:
            if sys.implementation.name == "micropython":
                sys.stdout.write("\n\n\nbailing - %s\n\n\n" % e)
            else:
                sys.stderr.write("bailing - %s\n\n\n" % e)
            break


# Main
if __name__ == '__main__':
    run()
