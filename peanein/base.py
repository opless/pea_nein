class Marshalling:

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
        return Qid(filetype, version, path)

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
        n, name = self.parse_string(data, ptr)
        ptr += n + 2
        n, uid = self.parse_string(data, ptr)
        ptr += n + 2
        n, gid = self.parse_string(data, ptr)
        ptr += n + 2
        n, muid = self.parse_string(data, ptr)
        # maybe an extra size check here?
        return size, Stat(name, qid, length, mode, typ, dev, atime, mtime, uid, gid, muid)

    def serialize_uint(self, num, size):
        return bytearray(int(num).to_bytes(size, 'little', signed=False))

    def str_to_pas(self, text):
        bin_text = bytearray(text.encode('utf-8'))
        size = bytearray(len(bin_text).to_bytes(2, 'little', signed=False))
        data = size + bin_text
        return data


class Qid(Marshalling):
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

    def __init__(self, filetype, version, path):
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
        return Qid(self.type, self.version, self.path)

    def is_opened(self):
        return self.private_data is not None

    def to_str(self):
        return "p=%d v=%d t=%d" % (self.path, self.version, self.type)


class Stat(Marshalling):
    DIR = 0x80000000
    APPEND = 0x40000000
    EXCL = 0x20000000

    def __init__(self, name: str, qid=Qid(Qid.QTDIR, 0, 0),
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
            if self.qid.is_mode(Qid.QTDIR):
                self.mode |= Stat.DIR | 0o111
            if self.qid.is_mode(Qid.QTAPPEND):
                self.mode |= Stat.APPEND
            if self.qid.is_mode(Qid.QTEXCL):
                self.mode |= Stat.EXCL

    def serialize(self) -> bytearray:
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

    def to_str(self) -> str:
        return "Stat: type:%02x,dev:%04x,qid(%s),mode=%04x,atime=%d,mtime=%d,length=%d,name=%s,uid=%s,gid=%s,mid=%s" % (
            self.type, self.dev, self.qid.to_str(),
            self.mode, self.atime, self.mtime, self.length,
            self.name, self.uid, self.gid, self.muid)


class FileSystemDriver:
    def io_size(self) -> int:
        raise IOError("IMPLEMENT ME: io_size")

    def reset(self):
        raise IOError("IMPLEMENT ME: reset")

    def get_root(self, name="") -> Qid:
        raise IOError("IMPLEMENT ME: get_root")

    def has_entry(self, qid: Qid, name: str) -> bool:
        raise IOError("IMPLEMENT ME: has_entry")

    def get_qid(self, qid: Qid, name: str) -> Qid:
        raise IOError("IMPLEMENT ME: get_qid")

    def get_stat(self, qid: Qid) -> Stat:
        raise IOError("IMPLEMENT ME: get_stat")

    def open_file(self, qid: Qid, mode: int):
        raise IOError("IMPLEMENT ME: open_file")

    def close_file(self, qid: Qid):
        raise IOError("IMPLEMENT ME: close_file")

    def read_file(self, qid: Qid, offset: int, count: int) -> bytearray:
        raise IOError("IMPLEMENT ME: read_file")

    def write_file(self, qid: Qid, offset: int, data: bytes) -> int:
        raise IOError("IMPLEMENT ME: write_file")
