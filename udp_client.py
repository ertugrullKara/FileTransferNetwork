import pickle as json
import socket
import time


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
        self._headers = {}
        self._data = {}
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
        sending_size = min((self.file_size - self.seq_to_send), self._max_packet_size)
        self._data = self.file_content[self.seq_to_send:self.seq_to_send+sending_size]
        self._headers["file_name"] = self.file_to_send
        self._headers["size_bytes"] = self.file_size

    def _middle_packets(self):
        sending_size = min((self.file_size - self.seq_to_send), self._max_packet_size)
        data = self.file_content[self.seq_to_send:self.seq_to_send+sending_size]
        self._headers["seq"] = self.seq_to_send
        self._data = data

    def _prepare_packet(self):
        if self.seq_to_send <= 0:
            self._initial_packet()
        else:
            self._headers = {}
            self._middle_packets()
        self._headers["seq"] = self.seq_to_send
        self.message = {"header": self._headers, "payload": self._data}

    def send_file(self, file_name="5mb.txt"):
        self.file_to_send = file_name
        self._open_file()
        while self.ack_came < self.file_size:
            self._prepare_packet()
            try:
                # Send message
                self.sock.sendto(json.dumps(self.message), (self.dest_ip[self.dest_ip_index], self.dest_port))
                self.response = json.loads(self.sock.recv(1024))
                print "Sent:"
                print self.message
                self._check_incoming_ack()
            except: # Timeout
                pass
            self.dest_ip_index = (self.dest_ip_index + 1) % len(self.dest_ip)   # Alternate between ip's. [Multi-homing]
            time.sleep(1)

    def _check_incoming_ack(self):
        incoming_ack = self.response["header"]["ack"]
        print "Incoming packet:"
        print self.response
        print "End\n"
        self.ack_came = int(incoming_ack)
        if self.ack_came  == self.seq_to_send:
            pass #Basarili
        else:
            # Bigger or lower ack
            self.seq_to_send = self.ack_came



if __name__ == "__main__":
    client = RDT_UDPClient(max_packet_size=10)
    client.send_file("5mb.txt")
