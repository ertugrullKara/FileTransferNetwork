import SocketServer as SS
import threading
import time


def utf8len(s):
	return len(s.encode('utf-8'))


class RDT_UDPHandler(SS.BaseRequestHandler):
	file_name = "default.txt"
	file_size = 0
	file = None
	last_succ_byte = 0
	waiting_for_byte = last_succ_byte + 1
	buffer = []
	package_coming = []

	def _init(self):
		self.file_name = self._headers["file_name"]
		self.file_size = self._headers["size_bytes"]
		self.file = open(self.file_name, 'wb')

	def _finish(self):
		if self.last_succ_byte != self.file_size:
			return False
		self.file.close()
		return True

	def __received_bytes__(self, bytes):
		self.last_succ_byte += bytes
		self.waiting_for_byte = self.last_succ_byte + 1

	def __check_send_ACK__(self):
		coming_seq_number = self._headers["seq"]

		if coming_seq_number == 0:
			# Initial packet has arrived.
			# Get properties.
			self._init()
			self.__received_bytes__(1)
		elif coming_seq_number + 1 == self.waiting_for_byte:
			# Expected package has arrived.
			# Update ACK message to send.
			msg_bytes = utf8len(self._message)
			self.__received_bytes__(msg_bytes)
			self.file.write(self._message)
			# Write buffered messages to file.
			self.buffer.sort(key=lambda tup: tup[0])
			for buffered_item in self.buffer:
				self.file.write(buffered_item[1])
				msg_bytes = utf8len(buffered_item[1])
				self.__received_bytes__(msg_bytes)
			self.buffer = []
		elif coming_seq_number + 1 > self.waiting_for_byte:
			# A packet that is ahead of me has arrived.
			# But save incoming packet to be processed later.
			self.buffer.append((coming_seq_number, self._message))
		elif coming_seq_number + 1 < self.waiting_for_byte:
			# Already arrived packet came again.
			# Just send the same ACK.
			pass
		elif self._headers["last"]:
			if self._finish():	# Finished.
				self.waiting_for_byte = -1
			else:				# Not finished. Send last ACK.
				pass
		else:
			print self._headers
			print self._data
			print "ERROR!"
			raise NotImplementedError

		# Send new ACK.
		self._send(self.waiting_for_byte)

	def _send(self, seq):
		socket = self.request[1]
		response = {"header":
			            {"ack": str(seq),
			             "last": False},
		            "payload": ""
		            }
		# TODO: Sender also must wait for 'last:True' message from server.
		socket.sendto(response, self.client_address)

	def handle(self):
		# Function to run when new UDP request came to the server.

		# Extract request
		self._data = self.request[0].strip()
		self._headers = self._data["header"]
		self._message = self._data["payload"]

		# TODO: Checksum?

		self.__check_send_ACK__()


class ThreadedUDPServer(SS.ThreadingMixIn, SS.UDPServer):
	pass


if __name__ == "__main__":
	# TODO: Multi-homing? Ana bir UDP portu olup buraya gelen her initial istek icin yeni socket acip,
	# TODO: sonrasinda gelen paketleri oralara yonlendirme gibi bir sey?
	USED_PORT = 8765
	HOST, PORT = "", USED_PORT

	# Open threaded-server for link.
	server = ThreadedUDPServer((HOST, PORT), RDT_UDPHandler)
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
