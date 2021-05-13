from peanein.server import Server
from peanein.base import FileSystemDriver, Stat, Qid
import socket
from noddy import Noddy



# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    addr = socket.getaddrinfo('0.0.0.0', 9999)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)

    print('listening on', addr)

    while True:
        cl, addr = s.accept()
        print('client connected from', addr)
        fd = cl.makefile('rwb', 0)
        print("client fd =", fd)
        srv = Server(fd, Noddy())
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
