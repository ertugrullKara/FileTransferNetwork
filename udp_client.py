import json
import socket
import sys
from timeit import default_timer as timer


def client(ip, port, message):
	# Open socket
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	# No connect in UDP.

	sock.settimeout(2.1)
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


def arg_process_u1(arg):
	# Process argument input and open 100 UDP clients.
	for _ in range(100):
		if arg.lower() == "t3":
			client("10.10.2.2", 21, json.dumps({"SRC": "10.10.2.1", "DEST": "10.10.5.2"}))
		if arg.lower() == "u3":
			client("10.10.2.2", 21, json.dumps({"SRC": "10.10.2.1", "DEST": "10.10.6.2"}))


if __name__ == "__main__":
	arg = sys.argv[1]
	arg_process_u1(arg)
