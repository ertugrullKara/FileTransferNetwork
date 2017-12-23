import json
import socket
import sys
from timeit import default_timer as timer


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

    def __init__(self, packet_size):
        self._packet_size = packet_size
        self._headers = {}
        self._data = {}
        self.seq_to_send = 0
        self.ack_came = 0
        self.file = None
        # Open socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.5)

    def _initial_packet(self):
        self.file = open(self.file_to_send, 'r')
        self._headers["file_name"] = self.file_to_send
        self._headers["size_bytes"] = utf8len(self.file.read())
        self.seq_to_send += 1

    def _middle_packets(self):
        data = self.file.read(600)
        self._headers["seq"] = self.seq_to_send
        self._data = data
        self.seq_to_send += 600

    def _prepare_packet(self):
        self._headers["seq"] = self.seq_to_send
        if self.seq_to_send <= 0:
            self._initial_packet()
        else:
            self._middle_packets()
        self.message = {"headers": self._headers, "payload": self._data}

    def send_file(self, file_name="5mb.txt"):
        self.file_to_send = file_name
        self._prepare_packet()
        try:
            # Send message
            self.sock.sendto(self.message, (self.dest_ip[self.dest_ip_index], self.dest_port))
            self.response = self.sock.recv(1024)
            self._check_incoming_ack()
        except: # Timeout
            pass

    def _check_incoming_ack(self):
        incoming_ack = self.response["headers"]["ack"]
        self.ack_came = incoming_ack
        if incoming_ack  == self.seq_to_send:
            pass #Basarili
        else:
            # Bigger or lower ack
            self.seq_to_send = incoming_ack



if __name__ == "__main__":
    client = RDT_UDPClient(packet_size=800)
    client.send_file("5mb.txt")
