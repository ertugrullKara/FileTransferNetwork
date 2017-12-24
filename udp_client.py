import hashlib
import socket
import sys
import time
from multiprocessing import Process, Queue
from threading import Lock, Thread

reload(sys)
sys.setdefaultencoding('utf8')

def utf8len(s):
    return len(s.encode('ascii'))

class RDT_UDPClient:
    dest_ip = ["10.10.2.2", "10.10.4.2"]
    dest_ip_index = 0
    dest_port = 8765
    file_to_send = "5mb.txt"
    seq_to_send = 0
    ack_came = 0
    file = None
    sock = None

    def __init__(self, max_packet_size):
        self._max_packet_size = max_packet_size
        self._headers = "_"
        self._data = ":"
        self.seq_to_send = 0
        self.ack_came = 0
        self.file = None
        # Open socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.estimated_rtt = 0.5
        self._rtt_alpha = 0.65

    def _open_file(self):
        self.file = open(self.file_to_send, 'rb')
        self.file_content = self.file.read()
        try:
            self.file_size = utf8len(self.file_content)
        except:
            self.file_size = len(self.file_content)

    def _initial_packet(self):
        self._headers = self.file_to_send + '_'
        self._headers += str(self.file_size) + '_'

    def _prepare_packet(self):
        if self.seq_to_send <= 0:
            self._initial_packet()
        else:
            self._headers = ""
        self._sending_size = min((self.file_size - self.seq_to_send), self._max_packet_size)
        self._data = self.file_content[self.seq_to_send:self.seq_to_send + self._sending_size]
        self._headers += str(self.seq_to_send)
        self.message = self._headers + self._data
        self.message = '{:05d}'.format(len(self._headers)) + self.message
        self.packeted_seq = self.seq_to_send
        self.seq_to_send += self._sending_size

    def _send_packet(self, queue, seq_to_send, message, sock, dest_ip, dest_port, rtt, last):
        try:
            # Send message
            sock.settimeout(rtt)
            print "Sending:",
            print seq_to_send
            message += hashlib.md5(message).digest()  # Checksum
            sent = time.time()
            sock.sendto(message, (dest_ip, dest_port))
            response = sock.recv(1024)
            rcvd = time.time()
            rtt = rtt * self._rtt_alpha + (1.0 - self._rtt_alpha) * (rcvd - sent)*100
            checksum = response[-16:]
            if hashlib.md5(response[:-16]).digest() != checksum:
                print "CHECKSUM ERROR - ACK"
                print response
                return
            header_len = int(response[:5])
            queue.put((int(response[5:5+header_len]), rtt))
        except:  # Timeout
            queue.put(("TIMEOUT", rtt*2))
        if last:
            queue.put(("END", rtt))

    def send_file(self, file_name="input.txt"):
        self.file_to_send = file_name
        self._open_file()
        queue = Queue()
        windowsize = min(int(( self.file_size / 1000 ) / 3.0), 1)    # Set window size. It can be any arbitrary number.
        while self.ack_came < self.file_size:
            for i in range(windowsize):
                self._prepare_packet()
                send_packet = Thread(target=self._send_packet, args=(queue, self.packeted_seq,
                                                                      self.message, self.sock,
                                                                      self.dest_ip[self.dest_ip_index],
                                                                      self.dest_port, self.estimated_rtt, i==(windowsize-1)))
                send_packet.daemon = True
                send_packet.start()
                self.dest_ip_index = (self.dest_ip_index + 1) % len(
                    self.dest_ip)  # Alternate between ip's. [Multi-homing]
            while True:
                try:
                    msg, new_rtt = queue.get(timeout=1)
                    if msg == "END":
                        break
                    elif msg == "TIMEOUT":
                        self.seq_to_send -= self._sending_size
                    else:
                        self._check_incoming_ack(msg)
                    self.estimated_rtt = new_rtt
                except:
                    print "Queue timeout."
                    break
        self._headers = "last"
        self.message = self._headers + ""
        self.message = '{:05d}'.format(len(self._headers)) + self.message
        self.message += hashlib.md5(self.message).digest()  # Checksum
        while 1:
            self.dest_ip_index = (self.dest_ip_index + 1) % len(
                self.dest_ip)  # Alternate between ip's. [Multi-homing]
            try:
                self.sock.sendto(self.message, (self.dest_ip[self.dest_ip_index], self.dest_port))
                response = self.sock.recv(1024)
                checksum = response[-16:]
                if hashlib.md5(response[:-16]).digest() != checksum:
                    return
                header_len = int(response[:5])
                if int(response[5:5 + header_len]) == -1:
                    break
            except:
                pass

    def _check_incoming_ack(self, incoming_ack):
        self.ack_came = incoming_ack
        print "Incoming ACK:",
        print self.ack_came
        if self.ack_came  == self.seq_to_send:
            pass #Basarili
        else:
            # Bigger or lower ack
            self.seq_to_send = self.ack_came



if __name__ == "__main__":
    client = RDT_UDPClient(max_packet_size=960)
    start = time.time()
    client.send_file(sys.argv[1])
    end = time.time()
    print "Elapsed time:", end-start
