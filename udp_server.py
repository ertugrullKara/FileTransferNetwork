import SocketServer as SS
import hashlib
import sys
import threading
import time

reload(sys)
sys.setdefaultencoding('utf8')

def utf8len(s):
    return len(s.encode('utf8'))

# Globals for threads to use
last_succ_byte = 0
waiting_for_byte = 0
file = None
file_name = "default.txt"
file_size = 0
allow_initial = True
buffer = []
processed_seqs = []
# Lock to use the globals from threads
_lock = threading.Lock()


class RDT_UDPHandler(SS.BaseRequestHandler):
    # RDTUDP Server class
    def _init(self):
        # Initialisations
        global file, file_name, file_size
        file_name = self._headers[0]
        file_size = int(self._headers[1])
        file = open(file_name, 'wb')

    def __received_bytes__(self, bytes):
        # Record how many bytes received right now
        global last_succ_byte, waiting_for_byte
        last_succ_byte += bytes
        waiting_for_byte = last_succ_byte

    def _write_message(self, msg, msg_bytes):
        # Write incoming message to file
        global file
        file.write(msg)
        # self.__received_bytes__(msg_bytes)

    def _save_message(self, msg, seq_num, msg_bytes):
        pass

    def _finish(self):
        # If received last ack, set everything to default value to allow another incoming file.
        global file, file_name, file_size, allow_initial, buffer, last_succ_byte, waiting_for_byte
        with _lock:
            buffer.sort(key=lambda tup: tup[0])
            for buffered_item in buffer:
                self._write_message(buffered_item[1], None)
            last_succ_byte = 0
            waiting_for_byte = 0
            file = None
            file_name = "default.txt"
            file_size = 0
            allow_initial = True
            buffer = []

    def __check_send_ACK__(self):
        # Checks incoming ACK message and determines the next action
        global allow_initial, buffer, processed_seqs
        coming_seq_number = int(self._headers[-1])
        print "Coming seq:",
        print coming_seq_number
        try:
            # If file is of type string
            msg_bytes = utf8len(self._message)
        except:
            # If file is of type byte
            msg_bytes = len(self._message)

        if coming_seq_number == 0 and allow_initial:
            # Initial packet has arrived.
            # Get properties.
            self._init()
            with _lock:
                # self._write_message(self._message, msg_bytes)
                allow_initial = False
                # buffer.sort(key=lambda tup: tup[0])
                # for buffered_item in buffer:
                #     try:
                #         msg_bytes = utf8len(buffered_item[1])
                #     except:
                #         msg_bytes = len(buffered_item[1])
                #     self._write_message(buffered_item[1], msg_bytes)
                # buffer = []
                if coming_seq_number not in processed_seqs:
                    self.__received_bytes__(msg_bytes)
                    processed_seqs.append(coming_seq_number)
                    buffer.append((coming_seq_number, self._message))
        elif coming_seq_number == waiting_for_byte:
            # Expected package has arrived.
            # Update ACK message to send.
            with _lock:
                # self._write_message(self._message, msg_bytes)
                # Write buffered messages to file.
                # buffer.sort(key=lambda tup: tup[0])
                for buffered_item in buffer:
                    if buffered_item[0] > waiting_for_byte and buffered_item[0] in processed_seqs:
                        continue
                    try:
                        msg_bytes = utf8len(buffered_item[1])
                    except:
                        msg_bytes = len(buffered_item[1])
                    self.__received_bytes__(msg_bytes)
                # buffer = []
                if coming_seq_number not in processed_seqs:
                    self.__received_bytes__(msg_bytes)
                    processed_seqs.append(coming_seq_number)
                    buffer.append((coming_seq_number, self._message))
        elif coming_seq_number > waiting_for_byte:
            # A packet that is ahead of me has arrived.
            # But save incoming packet to be processed later.
            with _lock:
                if coming_seq_number not in processed_seqs:
                    processed_seqs.append(coming_seq_number)
                    buffer.append((coming_seq_number, self._message))
        elif coming_seq_number < waiting_for_byte:
            # Already arrived packet came again.
            # Just send the same ACK.
            pass
        else:
            print self._data
            print "ERROR!"
            raise NotImplementedError

        # Send new ACK.
        print "Sending ACK:",
        print waiting_for_byte

    def _send(self, seq):
        # Send packet
        socket = self.request[1]
        response = str(seq)
        response = '{:05d}'.format(len(response)) + response
        # Put header length in the first 5 bytes of message for easy processing
        checksum = hashlib.md5(response).digest()
        socket.sendto(response + checksum, self.client_address)

    def handle(self):
        # Function to run when new UDP request came to the server.

        # Extract request
        self._data = self.request[0]
        # Extract header length from first 5 bytes
        header_len = int(self._data[:5])
        self._headers = self._data[5:5+header_len].split('_')
        if self._headers[-1] == "last":
            # Last ACK received.
            if waiting_for_byte == file_size:
                self._finish()
                self._send(-1)
            else:
                # But not expecting last ACK.
                self._send(waiting_for_byte)
            return
        self._message = self._data[5+header_len:-16]
        # Check incoming message's checksum
        self._checksum = self._data[-16:]
        if hashlib.md5(self._data[:-16]).digest() != self._checksum:
            print "CHECKSUM_ERROR"
            print "Sending ACK:",
            print waiting_for_byte
            self._send(waiting_for_byte)
            return

        self.__check_send_ACK__()
        self._send(waiting_for_byte)


class ThreadingUDPServer(SS.ThreadingMixIn, SS.UDPServer):
    pass


if __name__ == "__main__":
    USED_PORT = 8765
    HOST, PORT = "", USED_PORT

    # Open threaded-server for link.
    server = ThreadingUDPServer((HOST, PORT), RDT_UDPHandler)
    ip, port = server.server_address

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    # Exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()
    print "UDP Server running."
    while (1):
        # Do not close the main thread. Allows us to close all the threads with CTRL+C
        time.sleep(100)
