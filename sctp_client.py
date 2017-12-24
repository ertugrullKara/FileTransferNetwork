import socket
import sys
import sctp
import time


def utf8len(s):
    return len(s.encode('utf-8'))


class SCTPHandler:
    def __init__(self, filename):
        self.dest_ip_port_tuples = (("10.10.2.2", 8765), ("10.10.4.2", 8765))
        self.filename = filename
        self.file = open(self.filename, 'rb')
        self.file_content = self.file.read()
        self.file_size = utf8len(self.file_content)
        self.buffer_size = 980

    def send(self):
        sock = sctp.sctpsocket_tcp(socket.AF_INET)
        sock.connect(self.dest_ip_port_tuples[0])
        initial_info = self.filename + ':' + str(self.buffer_size) + ":" + str(self.file_size)
        sock.send(initial_info)
        read_bytes = 0
        while 1:
            next_pack = min(self.buffer_size, self.file_size - read_bytes)
            sock.send(self.file_content[read_bytes:read_bytes + next_pack])
            read_bytes += next_pack
            if read_bytes == self.file_size:
                break


if __name__ == "__main__":
    sctp_client = SCTPHandler(sys.argv[1])
    start = time.time()
    sctp_client.send()
    end = time.time()
    print "Elapsed time:", end-start
