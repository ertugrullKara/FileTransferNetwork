import json
import socket
import sys
from timeit import default_timer as timer


def utf8len(s):
    return len(s.encode('utf-8'))


def client(ip, port, message):
    start = timer()
    try:
        # Send message
        sock.sendto(message, (ip, port))

        # Wait for ACK or NACK message.
        response = sock.recv(1024)
    # print "ACKReceivedU1: {}".format(response)
    except:
        response = "NACK_U1_to_GATEWAY"
    finally:
        sock.close()
    end = timer()
    if "NACK" in response:
        print response
        # print (end - start) * 1000


class RDT_UDPClient:
    dest_ip = ""
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
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)

    def _initial_packet(self):
        self.file = open(self.file_to_send, 'r')
        self._headers["file_name"] = self.file_to_send
        self._headers["size_bytes"] = utf8len(self.file.read())

    def _middle_packets(self):
        pass

    def send_file(self, file_name="5mb.txt"):
        self.file_to_send = file_name



if __name__ == "__main__":
    client = RDT_UDPClient(packet_size=800)
    client.send_file("5mb.txt")
