from .base import Marshalling


class Protocol(Marshalling):
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

    def read(self, count):
        data = self._channel.read(count)
        if data is None:
            self.fatal("NeinP.read: no data returned.")
        elif data is None or len(data) != count:
            self.fatal("NeinP.read: len(data) %d != count: %d." % (len(data), count))
        return data

    def write(self, data):
        self._channel.write(data)

    def send(self, verb, tag, data=None):
        msg = self.serialize_uint(verb, 1)
        msg += self.serialize_uint(tag, 2)
        if not (data is None):
            msg += data
        size = len(msg) + 4
        self.write(self.serialize_uint(size, 4) + msg)

    def next(self):
        size = self.parse_uint(self.read(4), 0, 4)
        verb = self.parse_uint(self.read(1), 0, 1)
        tag = self.parse_uint(self.read(2), 0, 2)
        if (size + 4) > self._max_size:
            self.fatal("Packet is oversized.")
        # read rest of packet
        data = self.read(size - 7)

        name = self.verb_to_text(verb)

        is_client_message = (verb % 2) == 1
        if self.is_server and is_client_message:
            self.fatal("Server got Client message.")
        elif (not self.is_server) and (not is_client_message):
            self.fatal("Client got Server Message.")

        ##################################################### Version
        #       size[4] Tversion tag[2] msize[4] version[s]
        #       size[4] Rversion tag[2] msize[4] version[s]
        if verb == self.Tversion or verb == self.Rversion:
            msize = self.parse_uint(data, 0, 4)
            _, version = self.parse_string(data, 4)

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
            self.ServerAuth(tag, afid, uname, aname)

        #       size[4] Rauth tag[2] aqid[13]
        elif verb == self.Rauth:
            aqid = self.parse_qid(data, 0)
            self.ClientAuth(tag, aqid)

        ##################################################### ERROR
        # Terror is illegal
        elif verb == self.Terror:
            self.fatal("Terror is an illegal message. Aborting.")

        #       size[4] Rerror tag[2] ename[s]
        elif verb == self.Rerror:
            ename = self.parse_string(data, 0)
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
            mode = self.parse_uint(data, 4, 1)
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
        #    ("Other end reports: '%s' #%d" % (ename, tag))
        data = self.str_to_pas(ename)
        self.send(self.Rerror, tag, data)

        if fatal:
            self.fatal(ename)

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
