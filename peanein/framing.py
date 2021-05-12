import binascii


class Framing:
    def __init__(self, read_fd, write_fd):
        self.read_fd = read_fd
        self.write_fd = write_fd
        self.found = False
        self.announced = False
        self.target = "<HEXLIFY_FRAMING>"

    def announce(self):
        self.write_fd.write(self.target)
        self.announced = True

    def find(self):
        p = 0
        while p < 4:
            c = self.read_fd.read(1)
            if c is None:
                self.found = True
                return  # so next read is also EOF
            if ord(self.target[p]) == c:
                p = p + 1
        self.found = True

    def read(self, n):
        # check we have an initial header
        if not self.found:
            self.find()
        buffer = self.read_fd.read(n * 2)
        if buffer is None:
            return None
        try:
            return binascii.unhexlify(buffer)
        except ValueError:
            return None

    def write(self, data):
        if not self.announced:
            self.announce()

        buffer = binascii.hexlify(data)
        n = self.write_fd.write(buffer)
        return n / 2
