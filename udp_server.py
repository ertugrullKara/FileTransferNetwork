import SocketServer as SS
import threading
import time
import sys

reload(sys)
sys.setdefaultencoding('utf8')

def utf8len(s):
    return len(s.encode('utf8'))

last_succ_byte = 0
waiting_for_byte = 0
file = None
file_name = "default.txt"
file_size = 0
allow_initial = True
buffer = []
_lock = threading.Lock()


class RDT_UDPHandler(SS.BaseRequestHandler):
    def _init(self):
        global file, file_name, file_size
        file_name = self._headers[0]
        file_size = int(self._headers[1])
        file = open(file_name, 'wb')

    def __received_bytes__(self, bytes):
        global last_succ_byte, waiting_for_byte
        last_succ_byte += bytes
        waiting_for_byte = last_succ_byte

    def _write_message(self, msg, msg_bytes):
        global file
        file.write(msg)
        self.__received_bytes__(msg_bytes)

    def _finish(self):
        global file, file_name, file_size, allow_initial, buffer, last_succ_byte, waiting_for_byte
        with _lock:
            last_succ_byte = 0
            waiting_for_byte = 0
            file = None
            file_name = "default.txt"
            file_size = 0
            allow_initial = True
            buffer = []

    def __check_send_ACK__(self):
        global allow_initial, buffer
        coming_seq_number = int(self._headers[-1])
        print "Coming seq:",
        print coming_seq_number
        try:
            msg_bytes = utf8len(self._message)
        except:
            msg_bytes = len(self._message)

        if coming_seq_number == 0 and allow_initial:
            # Initial packet has arrived.
            # Get properties.
            self._init()
            with _lock:
                self._write_message(self._message, msg_bytes)
                allow_initial = False
                buffer.sort(key=lambda tup: tup[0])
                for buffered_item in buffer:
                    try:
                        msg_bytes = utf8len(buffered_item[1])
                    except:
                        msg_bytes = len(buffered_item[1])
                    self._write_message(buffered_item[1], msg_bytes)
                buffer = []
        elif coming_seq_number == waiting_for_byte:
            # Expected package has arrived.
            # Update ACK message to send.
            with _lock:
                self._write_message(self._message, msg_bytes)
                # Write buffered messages to file.
                buffer.sort(key=lambda tup: tup[0])
                for buffered_item in buffer:
                    try:
                        msg_bytes = utf8len(buffered_item[1])
                    except:
                        msg_bytes = len(buffered_item[1])
                    self._write_message(buffered_item[1], msg_bytes)
                buffer = []
        elif coming_seq_number > waiting_for_byte:
            # A packet that is ahead of me has arrived.
            # But save incoming packet to be processed later.
            with _lock:
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
        socket = self.request[1]
        response = str(seq) + ':'
        checksum = hash(response)
        socket.sendto(response + ":" + str(checksum), self.client_address)

    def handle(self):
        # Function to run when new UDP request came to the server.

        # Extract request
        self._data = self.request[0]
        print self._data
        self._headers = self._data.split(':')[0].split('_')
        if waiting_for_byte == file_size and self._headers[-1] == "last":
            self._finish()
            self._send(-1)
            print "\n\n\n"
            return
        self._message = self._data.split(':')[1]
        self._checksum = int(self._data.split(':')[2])
        if hash(":".join(self._data.split(':')[:-1])) != self._checksum:
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
