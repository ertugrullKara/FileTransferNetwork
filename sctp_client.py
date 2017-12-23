import socket

import sctp


class SCTPHandler:
	def __init__(self, ip, port, filename):
		self.dest_ip = ip
		self.dest_port = port
		self.filename = filename

	def send(self):
		sock = sctp.sctpsocket_tcp(socket.AF_INET)
		# sctp.bindx ?
		sock.connectx([(self.dest_ip, self.dest_port)])
