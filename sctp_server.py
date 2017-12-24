import socket
import sctp
import sys

reload(sys)
sys.setdefaultencoding('latin1')

class SCTPHandler:
    def __init__(self):
        self.dest_ip_port_tuples = (("10.10.2.2", 8765), ("10.10.4.2", 8765))
        self.filename = None
        self.sock = sctp.sctpsocket_tcp(socket.AF_INET)
        self.sock.bindx(self.dest_ip_port_tuples)
        self.sock.listen(10)

    def serve_forever(self):
        while 1:
            self.serve()

    def serve(self):
        connection, address = self.sock.accept()
        initial = connection.recv(1000)
        incoming = initial.split(':')
        self.total_size = int(incoming[2])
        self.buffer_size = int(incoming[1])
        self.filename = incoming[0]
        self.file = open(self.filename, 'wb')
        total = 0
        while 1:
            buf = connection.recv(self.buffer_size)
            if buf > 0:
                self.file.write(buf)
                total += len(buf)    # or buf ?
                if total == self.total_size:
                    break


if __name__ == "__main__":
    sctp_server = SCTPHandler()
    sctp_server.serve_forever()
