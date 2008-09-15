#!python

# $Id$

import os
import sys
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

import win32serviceutil
import win32service
from win32com.client import constants

class ForwardingService(win32serviceutil.ServiceFramework):
	"""
	_svc_name_:			The name of the service (used in the Windows registry).
						DEFAULT: The capitalized name of the current directory.
	_svc_display_name_: The name that will appear in the Windows Service Manager.
						DEFAULT: The capitalized name of the current directory.	   
	log_dir:			The desired location of the stdout and stderr
						log files.
						DEFAULT: %system%\LogFiles\%(_svc_display_name_)s
	"""
	_svc_name_ = 'dns_forward'										# The name of the service.
	_svc_display_name_ = 'DNS Forwarding Service'					# The Service Manager display name.
	log_dir = os.path.join(
		os.environ['SYSTEMROOT'],
		'System32',
		'LogFiles',
		_svc_display_name_,
		)		 													# The log directory for the stderr and 
																	# stdout logs.
	_target_host = '2002:41de:a625::41de:a625'
	
	# -- END USER EDIT SECTION
	
	def SvcDoRun(self):
		""" Called when the Windows Service runs. """
		self.init_logging()
		self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
		self.forwarder = Forwarder(self._target_host)
		self.ReportServiceStatus(win32service.SERVICE_RUNNING)
		self.forwarder.serve_forever()
	
	def SvcStop(self):
		"""Called when Windows receives a service stop request."""
		
		self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
		# todo: stop the forwarder
		# self.forwarder.stop()
		self.ReportServiceStatus(win32service.SERVICE_STOPPED)

	def init_logging(self):
		"redirect output to avoid crashing the service"
		os.makedirs(ForwardingService.log_dir)
		sys.stdout = open(os.path.join(ForwardingService.log_dir, 'stdout.log'), 'a')
		sys.stderr = open(os.path.join(ForwardingService.log_dir, 'stderr.log'), 'a')

def start_service():
	win32serviceutil.HandleCommandLine(ForwardingService)

def main():
	Forwarder(ForwardingService._target_host).serve_forever()

if __name__ == '__main__': main()