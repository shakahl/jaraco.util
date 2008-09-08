import sys
from socket import *

class EchoServer(object):
	def __init__(self):
		options, args = self.get_options()
		if args:
			raise RuntimeError, 'Incorrect arguments'
		self.serve(options)

	def get_options(self):
		from optparse import OptionParser
		parser = OptionParser()
		parser.add_option("-p", "--port",
						   help="listen on this port", type="int",
						   default=9999)
		return parser.parse_args()

	def serve(self, options):
		s = socket(AF_INET, SOCK_DGRAM)
		s.bind(('', options.port))
		while True:
			res, addr = s.recvfrom(1024)
			print res, addr

class Sender(object):
	def __init__(self):
		options, args = self.get_options()
		if len(args) != 0:
			raise RuntimeError, 'Bad arguments provided'
		self.send_message(options)
		
	def send_message(self, options):
		host, port = options.connect.split(':')
		port = int(port)
		s = socket(AF_INET, SOCK_DGRAM)
		s.connect((host, port))
		s.send(options.message)
		s.close()

	def get_options(self):
		from optparse import OptionParser
		parser = OptionParser()
		parser.add_option("-m", "--message",
						   help="send this message", default="message!")
		parser.add_option('-c', '--connect',
						   help="host:port to connect to",
						   default="localhost:9999")
		return parser.parse_args()

	def __repr__(self):
		return 'message sent'
		