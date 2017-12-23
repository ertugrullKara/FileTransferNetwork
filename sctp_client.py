import socket
import sctp


class SCTPHandler:
	def __init__(self, filename):
		self.dest_ip_port_tuples = (("10.10.2.2", 8765), ("10.10.4.2", 8765))
		self.filename = filename
		self.file = open(self.filename, 'wb')

	def send(self):
		sock = sctp.sctpsocket_tcp(socket.AF_INET)
		sock.connectx(self.dest_ip_port_tuples)
		sock.send(self.file.read())

if __name__ == "__main__":
	sctp_client = SCTPHandler("5mb.txt")
	sctp_client.send()