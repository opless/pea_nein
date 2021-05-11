#/usr/bin/python3
import sys,os
import random

from peanein.server import Server
from peanein.base import FileSystemDriver, Stat, Qid


class Noddy(FileSystemDriver):
    fs = {}
    qids = {}

    def __init__(self, io_size=4096):
        self.reset()
        self._io_size = io_size

    def io_size(self) -> int:
        return self._io_size

    def reset(self):
        self.fs = {}
        self.qids = {}
        self.f("/", Stat("/", Qid(Qid.QTDIR, 0, 0)))
        self.f("/dev", Stat("dev", Qid(Qid.QTDIR, 0, 1)))
        self.f("/dev/ttys", Stat("ttys", Qid(Qid.QTDIR, 0, 2)))
        self.f("/dev/random", Stat("random", Qid(Qid.QTFILE, 0, 11)))
        self.f("/dev/zero", Stat("zero", Qid(Qid.QTFILE, 0, 12)))
        self.f("/dev/null", Stat("null", Qid(Qid.QTFILE, 0, 13)))
        self.f("/dev/ttys/tty1", Stat("tty1", Qid(Qid.QTFILE, 0, 21)))
        self.f("/dev/ttys/tty2", Stat("tty2", Qid(Qid.QTFILE, 0, 22)))
        self.f("/dev/ttys/tty3", Stat("tty3", Qid(Qid.QTFILE, 0, 23)))
        self.f("/dev/ttys/tty4", Stat("tty4", Qid(Qid.QTFILE, 0, 24)))
        self.f("/dev/ttys/tty5", Stat("tty5", Qid(Qid.QTFILE, 0, 25)))

    def f(self, name, stat):
        self.fs[name] = stat
        self.qids[stat.qid.to_str()] = name

    def get_root(self) -> Qid:
        stat = self.fs['/']
        return stat.qid

    def has_entry(self, qid, name) -> bool:
        k = qid.to_str()
        if k in self.qids:
            prefix = self.qids[k]
            if prefix == "/":
                prefix = ""
            path = "%s/%s" % (prefix, name)
            if path in self.fs:
                return True
        return False

    def get_qid(self, qid, name) -> Qid:
        k = qid.to_str()
        if k in self.qids:
            prefix = self.qids[k]
            if prefix == "/":
                prefix = ""
            path = "%s/%s" % (prefix, name)
            if path in self.fs:
                return self.fs[path].qid
        return None  # Probably should throw an IOError

    def get_stat(self, qid) -> Stat:
        k = qid.to_str()
        if k in self.qids:
            name = self.qids[k]
            if name in self.fs:
                return self.fs[name]
        return None  # Probably should throw an IOError

    def open_file(self, qid: Qid, mode: int):
        # first check permissions

        k = qid.to_str()
        if qid.is_dir():  # do directory listing
            path = self.qids[k]
            if path == '/':
                slash_count = 1
            else:
                slash_count = path.count('/') + 1  # /foo/bar
            entries = []
            data = bytearray()
            for name in self.fs.keys():
                if name == "/":
                    continue
                if name.startswith(path) and name.count('/') == slash_count:
                    entries.append(name)
            for name in entries:
                stat = self.fs[name]
                data += stat.serialize()
            qid.private_data = data  # Stuff into private data

        else:  # do file opening
            qid.private_data = 0

    def close_file(self, qid: Qid):
        qid.private_data = None  # nothing more fancy required
        # except if it's opened as delete when closed, but not implemented here

    def read_file(self, qid: Qid, offset: int, count: int) -> bytearray:
        if qid.path == 11:  # random
            # ignore offset, spit out random bytes
            data = bytearray(random.getrandbits(8) for _ in range(count))

            # doesnt work on early cpython3 data = bytearray(random.randbytes(count))
            return data
        elif qid.path == 12:  # zero
            data = bytearray(b'\0' * count)
            return data
        elif qid.path == 13 or (qid.path > 20 and qid.path < 30):
            return bytearray()
        else:  # it's a dir
            length = len(qid.private_data)
            if offset >= length:
                return bytearray()
            # it's only going to send a little data, so don't worry about 8K packet limit?
            return qid.private_data[offset:]

    def write_file(self, qid: Qid, offset: int, data: bytes) -> int:
        # ignore all writes
        return len(data)
