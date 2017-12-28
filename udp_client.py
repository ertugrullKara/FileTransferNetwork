import hashlib
import socket
import sys
import os
import time
from multiprocessing import Process, Queue
from threading import Lock, Thread

reload(sys)
sys.setdefaultencoding('utf8')

def utf8len(s):
    return len(s.encode('ascii'))

class RDT_UDPClient:
    # RDTUDP Client class
    dest_ip_exp1 = ["10.10.4.2"]
    dest_ip_exp2 = ["10.10.2.2", "10.10.4.2"]
    dest_ip = dest_ip_exp1
    dest_ip_index = 0
    dest_port = 8765
    file_to_send = "5mb.txt"
    seq_to_send = 0
    ack_came = 0
    file = None
    sock = None

    def __init__(self, max_packet_size):
        # Initialisations
        self._max_packet_size = max_packet_size
        self._headers = "_"
        self._data = ":"
        self.seq_to_send = 0
        self.ack_came = 0
        self.prev_ack_came = 0
        self.prev_prev_ack_came = 0
        self.file = None
        # Open socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.estimated_rtt = 0.5
        self._rtt_alpha = 0.65

    def _open_file(self):
        # Open file and read the content
        self.file = open(self.file_to_send, 'rb')
        self.file_content = self.file.read()
        try:
            # If file is of type string
            self.file_size = utf8len(self.file_content)
        except:
            # If file is of type byte
            self.file_size = len(self.file_content)

    def _initial_packet(self):
        # Set headers for initial packet. To avoid unnecessary overhead of header,
        # filename and total file size are only send once in the initial packet.
        self._headers = self.file_to_send + '_'
        self._headers += str(self.file_size) + '_'

    def _prepare_packet(self):
        # Prepare a packet to send to server side.
        if self.seq_to_send <= 0:
            # If it is the first packet.
            self._initial_packet()
        else:
            self._headers = ""
        self._sending_size = min((self.file_size - self.seq_to_send), self._max_packet_size)
        self._data = self.file_content[self.seq_to_send:self.seq_to_send + self._sending_size]
        self._headers += str(self.seq_to_send)
        self.message = self._headers + self._data
        # Put header size in the first 5 bytes of the message for easy extraction.
        self.message = '{:05d}'.format(len(self._headers)) + self.message
        # Store current seq number and increase it to send next packet in the next call.
        self.packeted_seq = self.seq_to_send
        self.seq_to_send += self._sending_size

    def _send_packet(self, queue, seq_to_send, message, sock, dest_ip, dest_port, rtt, last):
        # Worker function to send a packet through a sock to destination.
        try:
            # rtt is estimated-rtt implementation. Constantly evolves to fit the network conditions.
            # Send message
            sock.settimeout(rtt)
            # print "Sending:",
            # print seq_to_send
            message += hashlib.md5(message).digest()  # Checksum in the last 16 bytes of the message
            sent = time.time()
            sock.sendto(message, (dest_ip, dest_port))
            response = sock.recv(1024)
            rcvd = time.time()
            rtt = min(rtt * self._rtt_alpha + (1.0 - self._rtt_alpha) * (rcvd - sent)*100, 0.5)
            # Check incoming ACK message's checksum
            checksum = response[-16:]
            if hashlib.md5(response[:-16]).digest() != checksum:
                print "CHECKSUM ERROR - ACK"
                print response
                return
            # Extract the header of ACK message. Only header in ACK messages are ACK numbers.
            header_len = int(response[:5])
            queue.put((int(response[5:5+header_len]), rtt))
        except:  # Timeout
            queue.put(("TIMEOUT", rtt + 0.5))
        if last:
            queue.put(("END", rtt))
        # Fill the queue with either ACK number, or TIMEOUT or END message.
        # Also put new estimated-rtt value to queue to update the timeout.
        return

    def send_file(self, file_name="input.txt", exp="1"):
        # Function to send a whole file
        if exp == "1":
            self.dest_ip = self.dest_ip_exp1
        elif exp == "2":
            self.dest_ip = self.dest_ip_exp2
        self.file_to_send = file_name
        self._open_file()
        queue = Queue()
        # Since an architecture like go-back-n is used, increasing windowsize too much decreases the performance.
        windowsize = min(int(( self.file_size / 1000 ) / 3.0), 25)    # Set window size. It can be any arbitrary number.
        while self.ack_came < self.file_size:
            for i in range(windowsize):
                # Pipelining. Prepare and send packet to a thread.
                self._prepare_packet()
                send_packet = Thread(target=self._send_packet, args=(queue, self.packeted_seq,
                                                                      self.message, self.sock,
                                                                      self.dest_ip[self.dest_ip_index],
                                                                      self.dest_port, self.estimated_rtt, i==(windowsize-1)))
                send_packet.daemon = True
                send_packet.start()
                # Alternate between ip's. [Multi-homing]
                self.dest_ip_index = (self.dest_ip_index + 1) % len(
                    self.dest_ip)
            while True:
                # Check thread's outputs
                try:
                    msg, new_rtt = queue.get(timeout=1)
                    self.estimated_rtt = new_rtt
                    if msg == "END":
                        break
                    elif msg == "TIMEOUT":
                        self.seq_to_send -= self._sending_size
                    else:
                        self._check_incoming_ack(msg)
                except:
                    print "Queue timeout."
                    break
        # When all file is sent, send finish signal. This message is also checksum protected.
        self._headers = "last"
        self.message = self._headers + ""
        self.message = '{:05d}'.format(len(self._headers)) + self.message
        self.message += hashlib.md5(self.message).digest()  # Checksum
        while 1:
            self.dest_ip_index = (self.dest_ip_index + 1) % len(
                self.dest_ip)  # Alternate between ip's. [Multi-homing]
            try:
                self.sock.settimeout(self.estimated_rtt+1)
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
        # Check incoming ack and decide on the next packet to send. Or exit the program since
        # the server received the whole file.
        self.ack_came = incoming_ack
        # print "Incoming ACK:",
        # print self.ack_came
        if self.ack_came == self.file_size:
            exit(1)
        elif self.ack_came  == self.seq_to_send:
            pass #Basarili
        else:
            if self.ack_came == self.prev_ack_came:
                if self.ack_came == self.prev_prev_ack_came:
                    # Bigger or lower ack
                    self.seq_to_send = self.ack_came
                else:
                    self.prev_prev_ack_came = self.prev_ack_came
                    self.prev_ack_came = self.ack_came
            else:
                self.prev_ack_came = 0
                self.prev_prev_ack_came = 0
        self.prev_ack_came = self.ack_came



if __name__ == "__main__":
    client = RDT_UDPClient(max_packet_size=960)
    start = time.time()
    client.send_file(sys.argv[1], sys.argv[2])
    end = time.time()
    print "Elapsed time:", end-start
