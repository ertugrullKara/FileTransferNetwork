import socket
import sys
import sctp
import time

reload(sys)
sys.setdefaultencoding('utf8')

def utf8len(s):
    return len(s.encode('utf8'))


class SCTPHandler:
    # SCTP Client class to send file
    def __init__(self, filename):
        # Initialisations
        self.dest_ip_exp1 = (("10.10.4.2", 8765),)
        self.dest_ip_exp2 = (("10.10.2.2", 8765), ("10.10.4.2", 8765))
        self.dest_ip_port_tuples = self.dest_ip_exp1
        self.filename = filename
        self.file = open(self.filename, 'rb')
        self.file_content = self.file.read()
        try:
            # If file is of type string
            self.file_size = utf8len(self.file_content)
        except:
            # If file is of type byte
            self.file_size = len(self.file_content)
        self.buffer_size = 980

    def send(self):
        # Open SCTP-TCP socket
        sock = sctp.sctpsocket_tcp(socket.AF_INET)
        try:    # IF Multihoming supported version of SCTP is installed
            sock.connectx(self.dest_ip_port_tuples)
            print "Multihoming."
        except: # Except, run without multihoming
            sock.connect(self.dest_ip_port_tuples[0])
        # Send initial info like filename etc
        initial_info = self.filename + ':' + str(self.buffer_size) + ":" + str(self.file_size)
        sock.send(initial_info)
        read_bytes = 0
        while 1:
            # Pack next bytes < 1000 and send
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
