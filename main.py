import random


class NeinMarshal:

    def parse_uint(self, data, ptr, size) -> int:
        if (ptr + size) > len(data):
            raise IOError("Bad conversion")
        return int.from_bytes(data[ptr:ptr + size], 'little', signed=False)

    def parse_string(self, data, ptr) -> (int, str):
        size = self.parse_uint(data, ptr, 2)
        ptr += 2
        if size > (len(data) - ptr):
            raise IOError("Bad string size.")
        text = data[ptr:ptr + size]
        return size, text.decode('utf-8')

    def parse_qid(self, data, ptr):
        if (len(data) - ptr) < 13:
            raise IOError("Bad Qid Size")
        filetype = self.parse_uint(data, ptr + 0, 1)
        version = self.parse_uint(data, ptr + 1, 4)
        path = self.parse_uint(data, ptr + 6, 8)
        return NeinQid(filetype, version, path)

    def parse_stat(self, data, ptr):
        size = self.parse_uint(data, ptr + 0, 2)
        typ = self.parse_uint(data, ptr + 2, 2)
        dev = self.parse_uint(data, ptr + 4, 4)
        qid = self.parse_qid(data, ptr + 8)
        mode = self.parse_uint(data, ptr + 21, 4)
        atime = self.parse_uint(data, ptr + 25, 4)
        mtime = self.parse_uint(data, ptr + 29, 4)
        length = self.parse_uint(data, ptr + 33, 4)
        ptr = ptr + 37
        xsize, name = self.parse_string(data, ptr)
        ptr += xsize + 2
        xsize, uid = self.parse_string(data, ptr)
        ptr += xsize + 2
        xsize, gid = self.parse_string(data, ptr)
        ptr += xsize + 2
        xsize, muid = self.parse_string(data, ptr)
        # TODO extra size check here?
        return size, NeinStat(name, qid, length, mode, typ, dev, atime, mtime, uid, gid, muid)

    def serialize_uint(self, num, size):
        return bytearray(int(num).to_bytes(size, 'little', signed=False))

    def str_to_pas(self, text):
        bin_text = bytearray(text.encode('utf-8'))
        size = bytearray(len(bin_text).to_bytes(2, 'little', signed=False))
        data = size + bin_text
        return data


class NeinQid(NeinMarshal):
    QTDIR = 0x80  # /* type bit for directories */
    QTAPPEND = 0x40  # /* type bit for append only files */
    QTEXCL = 0x20  # /* type bit for exclusive use files */
    QTMOUNT = 0x10  # /* type bit for mounted channel */
    QTAUTH = 0x08  # /* type bit for authentication file */
    QTTMP = 0x04  # /* type bit for not-backed-up file */
    QTFILE = 0x00  # /* plain file */

    type = 0  # bitmask for filetype QT constants above
    version = 0  # uint32 'version'
    path = 0  # uint64 'inode'

    private_data = None

    def __init__(self, filetype, version, path, is_opened=False):
        self.type = filetype
        self.path = path
        self.version = version

    def serialize(self):
        # data = bytearray(self.type.to_bytes(1, byteorder='little', signed=False))
        # data += bytearray(self.version.to_bytes(4, byteorder='little', signed=False))
        # data += bytearray(self.path.to_bytes(8, byteorder='little', signed=False))
        data = self.serialize_uint(self.type, 1)
        data += self.serialize_uint(self.version, 4)
        data += self.serialize_uint(self.path, 8)
        return data

    def is_mode(self, mode):
        return (mode & self.type) == mode

    def is_dir(self):
        return self.is_mode(self.QTDIR)

    def duplicate(self):
        return NeinQid(self.type, self.version, self.path)

    def is_opened(self):
        return self.private_data is not None

    def to_str(self):
        return "p=%d v=%d t=%d" % (self.path, self.version, self.type)


class NeinStat(NeinMarshal):
    DIR = 0x80000000
    APPEND = 0x40000000
    EXCL = 0x20000000

    def __init__(self, name: str, qid=NeinQid(NeinQid.QTDIR, 0, 0),
                 length=0, mode=None, typ=0, dev=0,
                 atime=0, mtime=0,
                 uid="default", gid="default", muid="default"):
        self.name = name
        self.qid = qid
        self.length = length
        self.mode = mode
        self.type = typ
        self.dev = dev
        self.atime = atime
        self.mtime = mtime
        self.uid = uid
        self.gid = gid
        self.muid = muid
        if self.mode is None:
            self.mode = 0o666  # rw-rw-rw-
            if self.qid.is_mode(NeinQid.QTDIR):
                self.mode |= NeinStat.DIR | 0o111
            if self.qid.is_mode(NeinQid.QTAPPEND):
                self.mode |= NeinStat.APPEND
            if self.qid.is_mode(NeinQid.QTEXCL):
                self.mode |= NeinStat.EXCL

    def serialize(self):
        data = self.serialize_uint(self.type, 2)
        data += self.serialize_uint(self.dev, 4)
        data += self.qid.serialize()
        data += self.serialize_uint(self.mode, 4)
        data += self.serialize_uint(self.atime, 4)
        data += self.serialize_uint(self.mtime, 4)
        data += self.serialize_uint(self.length, 8)
        data += self.str_to_pas(self.name)
        data += self.str_to_pas(self.uid)
        data += self.str_to_pas(self.gid)
        data += self.str_to_pas(self.muid)
        size = len(data)
        data = self.serialize_uint(size, 2) + data
        # data = self.serialize_uint(size+2, 2) + data
        return data

    def to_str(self):
        print(
            "NeinStat: type:%02x, dev:%04x, qid(%s),mode=%04x,atime=%d,mtime=%d,length=%d,name=%s,uid=%s,gid=%s,mid=%s"
            %
            (self.type, self.dev, self.qid.to_str(),
             self.mode, self.atime, self.mtime, self.length,
             self.name, self.uid, self.gid, self.muid))


class NeinFileSystemDriver:
    def io_size(self) -> int:
        raise IOError("IMPLEMENT ME: io_size")

    def reset(self):
        raise IOError("IMPLEMENT ME: reset")

    def get_root(self, name="") -> NeinQid:
        raise IOError("IMPLEMENT ME: get_root")

    def has_entry(self, qid: NeinQid, name: str) -> bool:
        raise IOError("IMPLEMENT ME: has_entry")

    def get_qid(self, qid: NeinQid, name: str) -> NeinQid:
        raise IOError("IMPLEMENT ME: get_qid")

    def get_stat(self, qid: NeinQid) -> NeinStat:
        raise IOError("IMPLEMENT ME: get_stat")

    def open_file(self, qid: NeinQid, mode: int) -> int:
        raise IOError("IMPLEMENT ME: open_file")

    def close_file(self, qid: NeinQid) -> int:
        raise IOError("IMPLEMENT ME: close_file")

    def read_file(self, qid: NeinQid, offset: int, count: int) -> bytearray:
        raise IOError("IMPLEMENT ME: read_file")

    def write_file(self, qid: NeinQid, offset: int, data: bytes) -> int:
        raise IOError("IMPLEMENT ME: write_file")


class NeinP(NeinMarshal):
    Tversion = 100
    Rversion = 101
    Tauth = 102
    Rauth = 103
    Tattach = 104
    Rattach = 105
    Terror = 106  # illegal
    Rerror = 107
    Tflush = 108
    Rflush = 109
    Twalk = 110
    Rwalk = 111
    Topen = 112
    Ropen = 113
    Tcreate = 114
    Rcreate = 115
    Tread = 116
    Rread = 117
    Twrite = 118
    Rwrite = 119
    Tclunk = 120
    Rclunk = 121
    Tremove = 122
    Rremove = 123
    Tstat = 124
    Rstat = 125
    Twstat = 126
    Rwstat = 127
    Tmax = 128
    Topenfd = 98
    Ropenfd = 99

    def __init__(self, channel, max_size=8192):
        print("NeinP init")
        self._channel = channel
        self._max_size = max_size
        self._configured_size = max_size
        self.is_server = True

    def verb_to_text(self, verb) -> str:
        verbs = ['Topenfd', 'Ropenfd', 'Tversion', 'Rversion',
                 'Tauth', 'Rauth', 'Tattach', 'Rattach',
                 'Terror', 'Rerror', 'Tflush', 'Rflush',
                 'Twalk', 'Rwalk', 'Topen', 'Ropen',
                 'Tcreate', 'Rcreate', 'Tread', 'Rread',
                 'Twrite', 'Rwrite', 'Tclunk', 'Rclunk',
                 'Tremove', 'Rremove', 'Tstat', 'Rstat',
                 'Twstat', 'Rwstat']
        if verb < self.Topenfd:
            return "#" + str(verb)
        if verb >= self.Tmax:
            return "#" + str(verb)
        return verbs[verb - self.Topenfd]

    def read(self, count=1):
        data = self._channel.read(count)
        if data is None or len(data) != count:
            raise EOFError("Short Read.")
        print("read", len(data), bytearray(data).hex(" ", bytes_per_sep=-2))
        return data

    def write(self, data):
        print("WRITING:", bytearray(data).hex(" ", bytes_per_sep=-2))
        print("........", data)
        self._channel.write(data)

    def send(self, verb, tag, data=None):
        msg = self.serialize_uint(verb, 1)
        msg += self.serialize_uint(tag, 2)
        if not (data is None):
            msg += data
        size = len(msg) + 4
        print("Writing ", verb, self.verb_to_text(verb), "tag", tag)
        self.write(self.serialize_uint(size, 4) + msg)

    def next(self):
        print("AWAITING NEXT MESSAGE")
        size = self.parse_uint(self.read(4), 0, 4)
        print("  Packet size is:", size)
        verb = self.parse_uint(self.read(1), 0, 1)
        print("  Verb identifier:", verb, self.verb_to_text(verb))
        tag = self.parse_uint(self.read(2), 0, 2)
        if (size + 4) > self._max_size:
            raise IOError("Packet is oversized.")
        # read rest of packet
        data = self.read(size - 7)

        name = self.verb_to_text(verb)

        is_client_message = (verb % 2) == 1
        if self.is_server and is_client_message:
            raise IOError("Server got Client message.")
        elif (not self.is_server) and (not is_client_message):
            raise IOError("Client got Server Message.")

        print("parsing:", verb, name, "tag=", tag, "data:", bytearray(data).hex(' ', bytes_per_sep=-2))

        ##################################################### Version
        #       size[4] Tversion tag[2] msize[4] version[s]
        #       size[4] Rversion tag[2] msize[4] version[s]
        if verb == self.Tversion or verb == self.Rversion:
            msize = self.parse_uint(data, 0, 4)
            _, version = self.parse_string(data, 4)
            print("  msize:", msize)
            print("  version:", version)

            if verb == self.Tversion:
                self.ServerVersion(tag, msize, version)
            else:
                self.ClientVersion(tag, msize, version)

        ##################################################### AUTH
        #       size[4] Tauth tag[2] afid[4] uname[s] aname[s]
        elif verb == self.Tauth:
            afid = self.parse_uint(data, 0, 4)
            uname_size, uname = self.parse_string(data, 4)
            aname_size, aname = self.parse_string(data, 6 + uname_size)
            print("  afid", afid)
            print("  uname", uname)
            print("  aname", aname)
            self.ServerAuth(tag, afid, uname, aname)

        #       size[4] Rauth tag[2] aqid[13]
        elif verb == self.Rauth:
            aqid = self.parse_qid(data, 0)
            print("  aqid", aqid)
            self.ClientAuth(tag, aqid)

        ##################################################### ERROR
        # Terror is illegal
        elif verb == self.Terror:
            raise IOError("Terror is an illegal message. Aborting.")

        #       size[4] Rerror tag[2] ename[s]
        elif verb == self.Rerror:
            ename = self.parse_string(data, 0)
            print("  ename", ename)
            self.Error(tag, ename)

        ##################################################### FLUSH
        #       size[4] Tflush tag[2] oldtag[2]
        elif verb == self.Tflush:
            oldtag = self.parse_uint(data, 0, 2)
            self.ServerFlush(tag, oldtag)

        #       size[4] Rflush tag[2]
        elif verb == self.Rflush:
            self.ClientFlush(tag)

        ##################################################### ATTACH
        #       size[4] Tattach tag[2] fid[4] afid[4] uname[s] aname[s]
        elif verb == self.Tattach:
            fid = self.parse_uint(data, 0, 4)
            afid = self.parse_uint(data, 4, 4)
            uname_size, uname = self.parse_string(data, 8)
            aname_size, aname = self.parse_string(data, 10 + uname_size)
            print("  fid", fid)
            print("  afid", afid)
            print("  uname", uname)
            print("  aname", aname)
            self.ServerAttach(tag, fid, afid, uname, aname)

        #       size[4] Rattach tag[2] qid[13]
        elif verb == self.Rattach:
            qid = self.parse_qid(data, 0)
            self.ClientAttach(tag, qid)

        ##################################################### WALK
        #       size[4] Twalk tag[2] fid[4] newfid[4] nwname[2]
        #       nwname*(wname[s])
        elif verb == self.Twalk:
            fid = self.parse_uint(data, 0, 4)
            newfid = self.parse_uint(data, 4, 4)
            count = self.parse_uint(data, 8, 2)
            ptr = 10
            wname_array = [None] * count
            for i in range(count):
                size, wname_array[i] = self.parse_string(data, ptr)
                ptr += size + 2
            self.ServerWalk(tag, fid, newfid, wname_array)

        #       size[4] Rwalk tag[2] nwqid[2] nwqid*(wqid[13])
        elif verb == self.Rwalk:
            count = self.parse_uint(data, 0, 2)
            wqid_array = [None] * count
            ptr = 2
            for i in range(count):
                wqid_array[i] = self.parse_qid(data, ptr)
                ptr += 13
            self.ClientWalk(tag, wqid_array)

        ##################################################### OPEN
        #       size[4] Topen tag[2] fid[4] mode[1]
        elif verb == self.Topen:
            fid = self.parse_uint(data, 0, 4)
            print("FID:", fid)
            mode = self.parse_uint(data, 4, 1)
            print("Mode:", mode)
            self.ServerOpen(tag, fid, mode)

        #       size[4] Ropen tag[2] qid[13] iounit[4]
        elif verb == self.Ropen:
            qid = self.parse_qid(data, 0)
            iounit = self.parse_uint(data, 13, 4)
            self.ClientOpen(tag, qid, iounit)

        ##################################################### CREATE
        #       size[4] Tcreate tag[2] fid[4] name[s] perm[4] mode[1]
        elif verb == self.Tcreate:
            fid = self.parse_uint(data, 0, 4)
            size, name = self.parse_string(data, 4)
            perm = self.parse_uint(data, 6 + size, 4)
            mode = self.parse_uint(data, 10 + size, 1)
            self.ServerCreate(tag, fid, name, perm, mode)

        #       size[4] Rcreate tag[2] qid[13] iounit[4]
        elif verb == self.Rcreate:
            qid = self.parse_qid(data, 0)
            iounit = self.parse_uint(data, 13, 4)
            self.ClientCreate(tag, qid, iounit)

        ##################################################### READ
        #       size[4] Tread tag[2] fid[4] offset[8] count[4]
        elif verb == self.Tread:
            fid = self.parse_uint(data, 0, 4)
            offset = self.parse_uint(data, 4, 8)
            count = self.parse_uint(data, 12, 4)
            self.ServerRead(tag, fid, offset, count)

        #       size[4] Rread tag[2] count[4] data[count]
        elif verb == self.Rread:
            count = self.parse_uint(data, 0, 4)
            buffer = data[4:4 + count]
            self.ClientRead(tag, buffer)

        ##################################################### WRITE
        # size[4] Twrite tag[2] fid[4] offset[8] count[4]
        #       data[count]
        elif verb == self.Twrite:
            fid = self.parse_uint(data, 0, 4)
            offset = self.parse_uint(data, 4, 8)
            count = self.parse_uint(data, 12, 4)
            buffer = data[16:16 + count]
            self.ServerWrite(tag, fid, offset, buffer)

        #       size[4] Rwrite tag[2] count[4]
        elif verb == self.Rwrite:
            count = self.parse_uint(data, 0, 4)
            self.ClientWrite(tag, count)

        ##################################################### CLUNK
        #       size[4] Tclunk tag[2] fid[4]
        elif verb == self.Tclunk:
            fid = self.parse_uint(data, 0, 4)
            self.ServerClunk(tag, fid)

        #       size[4] Rclunk tag[2]
        elif verb == self.Rclunk:
            self.ClientClunk(tag)

        ##################################################### REMOVE
        #       size[4] Tremove tag[2] fid[4]
        elif verb == self.Tremove:
            fid = self.parse_uint(data, 0, 4)
            self.ServerRemove(tag, fid)

        #       size[4] Rremove tag[2]
        elif verb == self.Rremove:
            self.ClientRemove(tag)

        ##################################################### STAT
        #       size[4] Tstat tag[2] fid[4]
        elif verb == self.Tstat:
            fid = self.parse_uint(data, 0, 4)
            self.ServerStat(tag, fid)

        #       size[4] Rstat tag[2] stat[n]
        elif verb == self.Rstat:
            size, stat = self.parse_stat(data, 0)
            self.ClientStat(tag, stat)

        ##################################################### WSTAT
        #       size[4] Twstat tag[2] fid[4] stat[n]
        elif verb == self.Twstat:
            fid = self.parse_uint(data, 0, 4)
            size, stat = self.parse_stat(data, 4)
            self.ServerWriteStat(tag, fid, stat)

        #       size[4] Rwstat tag[2]
        elif verb == self.Rwstat:
            self.ClientWriteStat(tag)

        ##################################################### OPENFD
        # TODO Topenfd/Ropenfd
        elif verb == self.Topenfd:
            raise Exception("TODO: Topenfd")
        elif verb == self.Ropenfd:
            raise Exception("TODO: Ropenfd")

        ##################################################### done.
        else:
            IOError("Unknown message #%d" % verb)

        return None

    ##################### YOU NEED TO OVERRIDE THESE

    def ServerVersion(self, tag, msize, version):
        raise Exception("TODO: Implement")

    def ClientVersion(self, tag, msize, version):
        raise Exception("TODO: Implement")

    def ServerAuth(self, tag, afid, uname, aname):
        raise Exception("TODO: Implement")

    def ClientAuth(self, tag, aqid):
        raise Exception("TODO: Implement")

    def Error(self, tag, ename, fatal=False):
        #    raise IOError("Other end reports: '%s' #%d" % (ename, tag))
        data = self.str_to_pas(ename)
        self.send(self.Rerror, tag, data)

        if fatal:
            raise IOError(ename)

    def ServerFlush(self, tag, oldtag):
        raise Exception("TODO: Implement")

    def ClientFlush(self, tag):
        raise Exception("TODO: Implement")

    def ServerAttach(self, tag, fid, afid, uname, aname):
        raise Exception("TODO: Implement")

    def ClientAttach(self, tag, qid):
        raise Exception("TODO: Implement")

    def ServerWalk(self, tag, fid, newfid, wname_array):
        raise Exception("TODO: Implement")

    def ClientWalk(self, tag, wqid_array):
        raise Exception("TODO: Implement")

    def ServerOpen(self, tag, fid, mode):
        raise Exception("TODO: Implement")

    def ClientOpen(self, tag, qid, iounit):
        raise Exception("TODO: Implement")

    def ServerCreate(self, tag, fid, name, perm, mode):
        raise Exception("TODO: Implement")

    def ClientCreate(self, tag, qid, iounit):
        raise Exception("TODO: Implement")

    def ServerRead(self, tag, fid, offset, count):
        raise Exception("TODO: Implement")

    def ClientRead(self, tag, buffer):
        raise Exception("TODO: Implement")

    def ServerWrite(self, tag, fid, offset, buffer):
        raise Exception("TODO: Implement")

    def ClientWrite(self, tag, count):
        raise Exception("TODO: Implement")

    def ServerClunk(self, tag, fid):
        raise Exception("TODO: Implement")

    def ClientClunk(self, tag):
        raise Exception("TODO: Implement")

    def ServerRemove(self, tag, fid):
        raise Exception("TODO: Implement")

    def ClientRemove(self, tag):
        raise Exception("TODO: Implement")

    def ServerStat(self, tag, fid):
        raise Exception("TODO: Implement")

    def ClientStat(self, tag, stat):
        raise Exception("TODO: Implement")

    def ServerWriteStat(self, tag, fid, stat):
        raise Exception("TODO: Implement")

    def ClientWriteStat(self, tag):
        raise Exception("TODO: Implement")

    def ServerOpenFD(self, tag, unknown):
        raise Exception("TODO: Implement")

    def ClientOpenFD(self, tag, unknown):
        raise Exception("TODO: Implement")

    NOFID = 0xffffffff
    NOTAG = 0xffff
    E_NEED_NOTAG = "NOTAG(0xFFFF) Required for Tversion."
    E_9P2000_ONLY = "We only talk 9P2000 Here."
    E_NO_AUTH = "No authentication required."
    E_NEED_NOFID = "No Authentication FID required."
    E_NO_ALT_ROOT = "Alternate root requested unavailable."
    E_INVALID_FID = "Supplied FID invalid."
    E_DUPLICATE_FID = "Supplied FID exists."
    E_NOT_DIR = "Not a directory."
    E_ALREADY_OPEN = "File already open."
    E_NOT_FOUND = "Not found."
    E_NOT_OPEN = "File not opened."


class NeinServer(NeinP):
    current_user = "default"
    fids = {}

    def __init__(self, channel, filesystem_driver: NeinFileSystemDriver, max_size=8192):
        print("NeinServer init")
        super().__init__(channel, max_size)
        self.filesystem_driver = filesystem_driver

    def add_fid(self, fid: int, qid: NeinQid):
        print("*** add ", fid, qid.to_str())
        self.fids[fid] = qid

    def get_fid(self, fid: int) -> NeinQid:
        if self.exists_fid(fid):
            return self.fids[fid]
        return None

    def del_fid(self, fid: int):
        if self.exists_fid(fid):
            del self.fids[fid]

    def init_fids(self):
        if self.fids is not None:
            for x in self.fids.keys():
                qid = self.fids[x]
                if qid.is_opened:
                    self.filesystem_driver.file_close(qid)
        self.fids = {}

    def exists_fid(self, fid: int) -> bool:
        return fid in self.fids

    def ServerVersion(self, tag, msize, version):
        print("* Tversion", tag, msize, version)
        # everything is cleared/reset on a Tversion
        self._max_size = self._configured_size
        self.init_fids()
        self.filesystem_driver.reset()

        if tag != self.NOTAG:
            self.Error(tag, self.E_NEED_NOTAG)

        if version != '9P2000':
            self.Error(tag, self.E_9P2000_ONLY, fatal=True)

        if msize < self._max_size:
            self._max_size = msize

        self.ClientVersion(tag, self._max_size, version)

    def ClientVersion(self, tag, msize, version):
        # size[4]  Rversion  tag[2]  msize[4]  version[s]
        data = self.serialize_uint(msize, 4)
        text = self.str_to_pas(version)
        data += text
        print("* Rversion", tag, msize, text)
        self.send(self.Rversion, tag, data)

    def ServerAuth(self, tag, afid, uname, aname):
        # No auth here, reply with error
        print("Tauth tag=%d afid=%d uname='%s' aname='%s'" % (tag, afid, uname, aname))
        self.Error(tag, self.E_NO_AUTH)

    def ServerAttach(self, tag, fid, afid, uname, aname):
        print("* Tattach tag=%d fid=%d afid=%d uname='%s' aname='%s'" % (tag, fid, afid, uname, aname))
        if afid != self.NOFID:
            self.Error(tag, self.E_NEED_NOFID)
            return
        if uname is None or len(uname.strip()) == 0:
            uname = "unset"
        # aname might be subtree.
        if aname is None:
            aname = ""
        if len(aname) != 0:
            self.Error(tag, self.E_NO_ALT_ROOT)
        else:
            qid = self.filesystem_driver.get_root()
            self.add_fid(fid, qid)
            self.ClientAttach(tag, qid)

    def ClientAttach(self, tag, qid):
        print("* Rattach tag=%d quid=" % tag, qid)
        data = qid.serialize()
        self.send(self.Rattach, tag, data)

    def ServerWalk(self, tag, fid, newfid, wname_array):
        print("* Twalk tag=%d fid=%d newfid=%d wname=" % (tag, fid, newfid), wname_array)
        # fetch the qid from the fid store
        qid = self.get_fid(fid)
        # consistency check, does FID exist?
        if qid is None:
            self.Error(tag, self.E_INVALID_FID)
            return
        # consistency check, we shouldn't have the supplied NEWFID
        if self.exists_fid(newfid):
            self.Error(tag, self.E_DUPLICATE_FID)
            return
        # QID must have not been created by a open or create
        if qid.is_opened():
            self.Error(tag, self.E_ALREADY_OPEN)
            return
        # shortcut, if there's no walking, just copy qid into newfid and have done with it
        if len(wname_array) == 0:
            self.add_fid(newfid, qid.duplicate())
            self.ClientWalk(tag, [])
            return
        # The fid must represent a directory unless zero path name elements are specified.
        if not qid.is_dir():
            self.Error(tag, self.E_NOT_DIR)
            return
        # now walk the fs tree
        qid_array = []
        print(".. Walking:")
        for name in wname_array:
            print(".... is there a name:", name, "in qid:", qid.to_str())
            if self.filesystem_driver.has_entry(qid, name):
                print(".... found")
                qid = self.filesystem_driver.get_qid(qid, name)
                print(".... qid:", qid.to_str())
                qid_array.append(qid)
            else:
                print(".... NOT FOUND!")
        # if success
        if len(qid_array) == len(wname_array):
            print(".. success:", newfid, "refers to:", qid.to_str())
            self.add_fid(newfid, qid)
        print(".. replying")
        self.ClientWalk(tag, qid_array)

    def ClientWalk(self, tag, wqid_array):
        print("* Rwalk tag=%d" % tag, wqid_array)
        # size[4] Rwalk tag[2] nwqid[2] nwqid*(qid[13])
        data = self.serialize_uint(len(wqid_array), 2)
        for qid in wqid_array:
            data += qid.serialize()
        self.send(self.Rwalk, tag, data)

    def ServerClunk(self, tag, fid):
        print("* Tclunk tag=%d fid=%d" % (tag, fid))
        if self.exists_fid(fid):
            qid = self.get_fid(fid)
            self.del_fid(fid)
            if qid.is_opened():
                self.filesystem_driver.close_file(qid)
        self.ClientClunk(tag)

    def ClientClunk(self, tag):
        print("* Rclunk tag=%d" % tag)
        self.send(self.Rclunk, tag, None)

    def ServerStat(self, tag, fid):
        print("* Tstat tag=%d fid=%d" % (tag, fid))
        qid = self.get_fid(fid)
        stat = self.filesystem_driver.get_stat(qid)
        self.ClientStat(tag, stat)

    def ClientStat(self, tag, stat):
        print("* Rstat tag=%d stat=%s" % (tag, stat.to_str()))
        data = stat.serialize()

        # Add extra length due to a bug in the actual implementations
        size = len(data)
        data = self.serialize_uint(size, 2) + data

        self.send(self.Rstat, tag, data)

    def ServerOpen(self, tag, fid, mode):
        print("* Topen tag=%d, fid=%d, mode=%02x" % (tag, fid, mode))
        if not self.exists_fid(fid):
            print(".. E_INVALID_FID")
            self.Error(tag, self.E_INVALID_FID)
            return
        qid = self.get_fid(fid)
        print(".. QID:", qid.to_str())
        if qid.is_opened():
            print(".. E_ALREADY_OPEN")
            self.Error(tag, self.E_ALREADY_OPEN)
            return
        print(".. opening file in the driver.")
        self.filesystem_driver.open_file(qid, mode)
        print(".. responding")
        self.ClientOpen(tag, qid, self.filesystem_driver.io_size())

    def ClientOpen(self, tag, qid, iounit):
        print("* Ropen tag=%d qid=%s, iounit=%d" % (tag, qid, iounit))
        data = qid.serialize()
        data += self.serialize_uint(iounit, 4)
        self.send(self.Ropen, tag, data)

    def ServerRead(self, tag, fid, offset, count):
        print("* Tread tag=%d fid=%d offset=%d count=%d" %
              (tag, fid, offset, count))
        if not self.exists_fid(fid):
            print(".. E_INVALID_FID")
            self.Error(tag, self.E_INVALID_FID)
            return
        qid = self.get_fid(fid)
        print(".. QID:", qid.to_str())
        if not qid.is_opened():
            self.Error(tag, self.E_NOT_OPEN)
            return
        print(".. calling fsdriver.")
        buffer = self.filesystem_driver.read_file(qid, offset, count);
        self.ClientRead(tag, buffer)

    def ClientRead(self, tag, buffer):
        print("* Rread tag=%d,buffer=" % tag, buffer)
        length = len(buffer)
        data = self.serialize_uint(length, 4) + buffer
        print(".. adding length:", length)
        self.send(self.Rread, tag, data)

    def ServerWrite(self, tag, fid, offset, buffer):
        print("* Twrite tag=%d, fid=%d, offset=%d, buffer=" % (tag, fid, offset), buffer)
        if not self.exists_fid(fid):
            print(".. E_INVALID_FID")
            self.Error(tag, self.E_INVALID_FID)
            return
        qid = self.get_fid(fid)
        print(".. QID:", qid.to_str())
        if not qid.is_opened():
            print(".. E_NOT_OPEN")
            self.Error(tag, self.E_NOT_OPEN)
            return
        print(".. calling fsdriver")
        count = self.filesystem_driver.write_file(qid, offset, buffer)
        print(".. count returned:", count)
        self.ClientWrite(tag, count)

    def ClientWrite(self, tag, count):
        print("*Rwrite tag=%d, count=%d" % (tag, count))
        self.send(self.Rwrite, tag, self.serialize_uint(count, 4))

    def ServerWriteStat(self, tag, fid, stat):
        print("* Rwstat tag=%d, fid=%d, stat=%s" % (tag, fid, stat))
        # no-op
        self.ClientWriteStat(tag)

    def ClientWriteStat(self, tag):
        self.send(self.Rwstat, tag)


# a very badly written filesystem driver
class Noddy(NeinFileSystemDriver):
    def __init__(self, io_size=4096):
        self.reset()
        self._io_size = io_size

    def io_size(self) -> int:
        return self._io_size

    def reset(self):
        self.fs = {}
        self.qids = {}
        self.f("/", NeinStat("/", NeinQid(NeinQid.QTDIR, 0, 0)))
        self.f("/dev", NeinStat("dev", NeinQid(NeinQid.QTDIR, 0, 1)))
        self.f("/dev/ttys", NeinStat("ttys", NeinQid(NeinQid.QTDIR, 0, 2)))
        self.f("/dev/random", NeinStat("random", NeinQid(NeinQid.QTFILE, 0, 11)))
        self.f("/dev/zero", NeinStat("zero", NeinQid(NeinQid.QTFILE, 0, 12)))
        self.f("/dev/null", NeinStat("null", NeinQid(NeinQid.QTFILE, 0, 13)))
        self.f("/dev/ttys/tty1", NeinStat("tty1", NeinQid(NeinQid.QTFILE, 0, 21)))
        self.f("/dev/ttys/tty2", NeinStat("tty2", NeinQid(NeinQid.QTFILE, 0, 22)))
        self.f("/dev/ttys/tty3", NeinStat("tty3", NeinQid(NeinQid.QTFILE, 0, 23)))
        self.f("/dev/ttys/tty4", NeinStat("tty4", NeinQid(NeinQid.QTFILE, 0, 24)))
        self.f("/dev/ttys/tty5", NeinStat("tty5", NeinQid(NeinQid.QTFILE, 0, 25)))

    def f(self, name, stat):
        self.fs[name] = stat
        self.qids[stat.qid.to_str()] = name

    def get_root(self) -> NeinQid:
        print("+ get_root")
        stat = self.fs['/']
        print("++ stat=", stat.to_str())
        return stat.qid

    def has_entry(self, qid, name) -> bool:
        print("+ has_entry: qid=", qid.to_str(), 'name=', name)
        k = qid.to_str()
        print("++ qids:", self.qids)
        if k in self.qids:
            prefix = self.qids[k]
            if prefix == "/":
                prefix = ""
            print("++ prefix=", prefix)
            path = "%s/%s" % (prefix, name)
            print("++ path=", path)
            print("++ self.fs.keys()=", list(self.fs.keys()))
            if path in self.fs:
                print("++ returning true")
                return True
        print("++ returning false")
        return False

    def get_qid(self, qid, name) -> NeinQid:
        k = qid.to_str()
        if k in self.qids:
            prefix = self.qids[k]
            if prefix == "/":
                prefix = ""
            path = "%s/%s" % (prefix, name)
            if path in self.fs:
                return self.fs[path].qid
        return None

    def get_stat(self, qid) -> NeinStat:
        k = qid.to_str()
        if k in self.qids:
            name = self.qids[k]
            if name in self.fs:
                return self.fs[name]
        return None

    def open_file(self, qid: NeinQid, mode: int) -> int:
        # first check permissions

        k = qid.to_str()
        if qid.is_dir():  # do directory listing
            path = self.qids[k]
            if path == '/':
                slashcount = 1
            else:
                slashcount = path.count('/') + 1  # /foo/bar
            entries = []
            data = bytearray()
            for name in self.fs.keys():
                if name == "/":
                    continue
                if name.startswith(path) and name.count('/') == slashcount:
                    entries.append(name)
            for name in entries:
                stat = self.fs[name]
                print("... entry: ", name, "stat=", stat.to_str())
                data += stat.serialize()
            qid.private_data = data  # Stuff into private data

        else:  # do file opening
            qid.private_data = 0

    def close_file(self, qid: NeinQid) -> int:
        qid.private_data = None  # nothing more fancy required
        # except if it's opened as delete when closed, but not implemented here

    def read_file(self, qid: NeinQid, offset: int, count: int) -> bytearray:
        print("FS: read_file qid=%s,offset=%d,count=%d" %
              (qid.to_str(), offset, count))
        data = bytearray()
        if qid.path == 11:  # random
            print("... random")
            # ignore offset, spit out random bytes
            data = bytearray(random.randbytes(count))
            return data
        elif qid.path == 12:  # zero
            print("... zero")
            data = bytearray(b'\0' * count)
            return data
        elif qid.path == 13 or (qid.path > 20 and qid.path < 30):
            print("... other (send nothing)")
            return bytearray()
        else:  # it's a dir
            length = len(qid.private_data)
            if offset >= length:
                return bytearray()
            # it's only going to send a little data, so don't worry about 8K packet limit?
            return qid.private_data[offset:]

    def write_file(self, qid: NeinQid, offset: int, data: bytes) -> int:
        # ignore all writes
        return len(data)


import socket

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    addr = socket.getaddrinfo('0.0.0.0', 564)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)

    print('listening on', addr)

    while True:
        cl, addr = s.accept()
        print('client connected from', addr)
        fd = cl.makefile('rwb', 0)
        print("client fd =", fd)
        srv = NeinServer(fd, Noddy())
        while True:
            try:
                srv.next()
            except EOFError as x:
                print("EOF:", x)
                break
            except IOError as e:
                print("listening again...", e)
                break
        cl.close()
    pass
