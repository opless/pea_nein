#/usr/bin/python3
import sys,os,io
import random

from peanein.server import Server
from peanein.base import FileSystemDriver, Stat, Qid

from noddy import Noddy


class StdioWrapper:
    def read(self, n = -1):
        return os.read(0,n)

    def write(self, s):
        return os.write(1,s)


# NOTE: this does not work under unix micropython because sys.stdin is a TextIOWrapper

class MicroPythonStdioWrapper(io.BaseIO):
    def __init__(self):
        if sys.implementation.name != "micropython":
            raise OSError("This is not micropython")

    def read(self, n= 32):

        buff = sys.stdin.read(n)
        data = buff.encode('utf-8')

        return data

    def write(self, s):
        n =  sys.stdout.write(s)
        return n


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    if sys.implementation.name == "micropython":
        import micropython
        micropython.kbd_intr(-1)
        IOError = OSError
        fd = MicroPythonStdioWrapper()
    else:
        fd = StdioWrapper()

    srv = Server(fd,Noddy())

    while True:
        try:
            srv.next()
        except Exception as e:
            sys.stderr.write("bailing - %s\n\n\n" % e)
            break
