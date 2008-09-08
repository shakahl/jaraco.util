#!python

# $Id$

import socket

port = socket.getservbyname('domain')

class Forwarder(object):
	dest_addr = ('::1', port)
	def __init__(self, listen_address):
		self.socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
		address = (listen_address, port)
		self.socket.bind(address)
		# set a timeout so the service can terminate gracefully
		self.socket.settimeout(2)
		self.dest = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
		self.dest.settimeout(2)

	def serve_forever(self):
		while True:
			self.relay_message()

	def relay_message(self):
		try:
			mesg, requester = self.socket.recvfrom(2**16)
			self.dest.sendto(mesg, self.dest_addr)
			resp = self.dest.recv(2**16)
			self.socket.sendto(resp, requester)
		except socket.timeout:
			pass

def main():
	Forwarder('2002:41de:a625::41de:a625').serve_forever()

if __name__ == '__main__': main()