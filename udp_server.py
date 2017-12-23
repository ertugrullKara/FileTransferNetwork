import SocketServer as SS
import threading
import time
import json


def utf8len(s):
    return len(s.encode('utf-8'))

last_succ_byte = 0
waiting_for_byte = 0
file = None

class RDT_UDPHandler(SS.BaseRequestHandler):
    file_name = "default.txt"
    file_size = 0
    file = None
    buffer = []
    package_coming = []

    def _init(self):
        global file
        self.file_name = self._headers[0]
        self.file_size = int(self._headers[1])
        file = open(self.file_name, 'wb')

    def _finish(self):
        global file
        if last_succ_byte != self.file_size:
            return False
        file.close()
        return True

    def __received_bytes__(self, bytes):
        global last_succ_byte, waiting_for_byte
        last_succ_byte += bytes
        waiting_for_byte = last_succ_byte

    def __check_send_ACK__(self):
        global last_succ_byte, waiting_for_byte, file
        coming_seq_number = int(self._headers[-1])
        msg_bytes = utf8len(self._message)
        print "Check ACK"
        print coming_seq_number, waiting_for_byte
        print "Packet end.\n"

        if coming_seq_number == 0:
            # Initial packet has arrived.
            # Get properties.
            self._init()
            file.write(self._message)
            self.__received_bytes__(msg_bytes)
        elif coming_seq_number == waiting_for_byte:
            # Expected package has arrived.
            # Update ACK message to send.
            self.__received_bytes__(msg_bytes)
            file.write(self._message)
            # Write buffered messages to file.
            self.buffer.sort(key=lambda tup: tup[0])
            for buffered_item in self.buffer:
                file.write(buffered_item[1])
                msg_bytes = utf8len(buffered_item[1])
                self.__received_bytes__(msg_bytes)
            self.buffer = []
        elif coming_seq_number + msg_bytes == self.file_size:
            self._finish()  # Finished.
            waiting_for_byte = -1
        elif coming_seq_number + 1 > waiting_for_byte:
            # A packet that is ahead of me has arrived.
            # But save incoming packet to be processed later.
            self.buffer.append((coming_seq_number, self._message))
        elif coming_seq_number + 1 < waiting_for_byte:
            # Already arrived packet came again.
            # Just send the same ACK.
            pass
        else:
            print self._data
            print "ERROR!"
            raise NotImplementedError

        # Send new ACK.
        self._send(waiting_for_byte)

    def _send(self, seq):
        socket = self.request[1]
        response = str(seq) + ':'
        socket.sendto(json.dumps(response), self.client_address)

    def handle(self):
        # Function to run when new UDP request came to the server.

        # Extract request
        self._data = self.request[0].strip()
        self._headers = self._data.split(':')[0].split('_')
        self._message = self._data.split(':')[1]
        print self._data

        # TODO: Checksum?

        self.__check_send_ACK__()


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
