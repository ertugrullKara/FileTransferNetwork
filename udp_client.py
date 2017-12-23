import socket
import time
from multiprocessing import Process
from Queue import Queue

def utf8len(s):
    return len(s.encode('utf-8'))


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
        self._max_packet_size = max_packet_size + 1
        self._headers = "_"
        self._data = ":"
        self.seq_to_send = 0
        self.ack_came = 0
        self.file = None
        # Open socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.5)

    def _open_file(self):
        self.file = open(self.file_to_send, 'rb')
        self.file_content = self.file.read()
        self.file_size = utf8len(self.file_content)

    def _initial_packet(self):
        self._headers = self.file_to_send + '_'
        self._headers += str(self.file_size) + '_'

    def _prepare_packet(self):
        if self.seq_to_send <= 0:
            self._initial_packet()
        else:
            self._headers = "_"
        sending_size = min((self.file_size - self.seq_to_send), self._max_packet_size)
        self._data = self.file_content[self.seq_to_send:self.seq_to_send + sending_size]
        self._headers += str(self.seq_to_send)
        self.message = self._headers + ':' + self._data

    def _send_packet(self, queue, last):
        try:
            # Send message
            print "Sending:",
            print self.seq_to_send
            self.message += ':' + str(hash(self.message))  # Checksum
            self.sock.sendto(self.message, (self.dest_ip[self.dest_ip_index], self.dest_port))
            self.response = self.sock.recv(1024)
            queue.put(int(self.response.split(':')[0]))
        except:  # Timeout
            pass
        if last:
            queue.put("END")

    def send_file(self, file_name="5mb.txt"):
        self.file_to_send = file_name
        self._open_file()
        queue = Queue()
        windowsize = 2
        while self.ack_came < self.file_size:
            for i in range(windowsize):
                self._prepare_packet()
                send_packet = Process(target=self._send_packet, args=(queue, i==windowsize-1))
                send_packet.daemon = True
                send_packet.start()
            while True:
                msg = queue.get()
                if msg != "END":
                    self._check_incoming_ack(msg)
                else:
                    break
            self.dest_ip_index = (self.dest_ip_index + 1) % len(self.dest_ip)   # Alternate between ip's. [Multi-homing]

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
    client = RDT_UDPClient(max_packet_size=10)
    client.send_file("5mb.txt")
