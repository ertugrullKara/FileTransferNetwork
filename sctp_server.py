import socket
import sctp


class SCTPHandler:
    def __init__(self, filename):
        self.dest_ip_port_tuples = (("10.10.2.2", 8765), ("10.10.4.2", 8765))
        self.filename = filename
        self.file = open(self.filename, 'wb')

    def serve(self):
        sock = sctp.sctpsocket_tcp(socket.AF_INET)
        sock.bindx(self.dest_ip_port_tuples)
        sock.listen(10)

        while 1:
            connection, address = sock.accept()
            buf = connection.recv(1024)
            if len(buf) > 0:
                print buf
                break


if __name__ == "__main__":
    sctp_server = SCTPHandler("5mb.txt")
    sctp_server.serve()
