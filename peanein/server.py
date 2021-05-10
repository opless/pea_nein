from peanein.base import Qid, FileSystemDriver
from peanein.protocol import Protocol


class Server(Protocol):
    current_user = "default"
    fids = {}

    def __init__(self, channel, filesystem_driver: FileSystemDriver, max_size=8192):
        super().__init__(channel, max_size)
        self.filesystem_driver = filesystem_driver

    def add_fid(self, fid: int, qid: Qid):
        self.fids[fid] = qid

    def get_fid(self, fid: int) -> Qid:
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
                    self.filesystem_driver.close_file(qid)
        self.fids = {}

    def exists_fid(self, fid: int) -> bool:
        return fid in self.fids

    def ServerVersion(self, tag, msize, version):
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
        self.send(self.Rversion, tag, data)

    def ServerAuth(self, tag, afid, uname, aname):
        # No auth here, reply with error
        self.Error(tag, self.E_NO_AUTH)

    def ServerAttach(self, tag, fid, afid, uname, aname):
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
        data = qid.serialize()
        self.send(self.Rattach, tag, data)

    def ServerWalk(self, tag, fid, newfid, wname_array):
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
        for name in wname_array:
            if self.filesystem_driver.has_entry(qid, name):
                qid = self.filesystem_driver.get_qid(qid, name)
                qid_array.append(qid)
        # if success
        if len(qid_array) == len(wname_array):
            self.add_fid(newfid, qid)
        self.ClientWalk(tag, qid_array)

    def ClientWalk(self, tag, wqid_array):
        # size[4] Rwalk tag[2] nwqid[2] nwqid*(qid[13])
        data = self.serialize_uint(len(wqid_array), 2)
        for qid in wqid_array:
            data += qid.serialize()
        self.send(self.Rwalk, tag, data)

    def ServerClunk(self, tag, fid):
        if self.exists_fid(fid):
            qid = self.get_fid(fid)
            self.del_fid(fid)
            if qid.is_opened():
                self.filesystem_driver.close_file(qid)
        self.ClientClunk(tag)

    def ClientClunk(self, tag):
        self.send(self.Rclunk, tag, None)

    def ServerStat(self, tag, fid):
        qid = self.get_fid(fid)
        stat = self.filesystem_driver.get_stat(qid)
        self.ClientStat(tag, stat)

    def ClientStat(self, tag, stat):
        data = stat.serialize()

        # Add extra length due to a bug in the actual implementations
        size = len(data)
        data = self.serialize_uint(size, 2) + data

        self.send(self.Rstat, tag, data)

    def ServerOpen(self, tag, fid, mode):
        if not self.exists_fid(fid):
            self.Error(tag, self.E_INVALID_FID)
            return
        qid = self.get_fid(fid)
        if qid.is_opened():
            self.Error(tag, self.E_ALREADY_OPEN)
            return
        self.filesystem_driver.open_file(qid, mode)
        self.ClientOpen(tag, qid, self.filesystem_driver.io_size())

    def ClientOpen(self, tag, qid, iounit):
        data = qid.serialize()
        data += self.serialize_uint(iounit, 4)
        self.send(self.Ropen, tag, data)

    def ServerRead(self, tag, fid, offset, count):
        if not self.exists_fid(fid):
            self.Error(tag, self.E_INVALID_FID)
            return
        qid = self.get_fid(fid)
        if not qid.is_opened():
            self.Error(tag, self.E_NOT_OPEN)
            return
        buffer = self.filesystem_driver.read_file(qid, offset, count)
        self.ClientRead(tag, buffer)

    def ClientRead(self, tag, buffer):
        length = len(buffer)
        data = self.serialize_uint(length, 4) + buffer
        self.send(self.Rread, tag, data)

    def ServerWrite(self, tag, fid, offset, buffer):
        if not self.exists_fid(fid):
            self.Error(tag, self.E_INVALID_FID)
            return
        qid = self.get_fid(fid)
        if not qid.is_opened():
            self.Error(tag, self.E_NOT_OPEN)
            return
        count = self.filesystem_driver.write_file(qid, offset, buffer)
        self.ClientWrite(tag, count)

    def ClientWrite(self, tag, count):
        self.send(self.Rwrite, tag, self.serialize_uint(count, 4))

    def ServerWriteStat(self, tag, fid, stat):
        # no-op
        self.ClientWriteStat(tag)

    def ClientWriteStat(self, tag):
        self.send(self.Rwstat, tag)

