# -*- coding: UTF-8 -*-

"""IPTools
Tools for IP communication.

Objects:
	PortScanner: scans a range of ports
	PortListener: listens on a port
	PortRangeListener: listens on a range of ports
	
Copyright © 2004 Sandia National Laboratories  
"""

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Revision: 2 $a'[11:-2]
__svnauthor__ = '$Author: Jaraco $'[9:-2]
__date__ = '$Date: 04-06-23 12:24 $'[7:-2]

import threading, socket, sys, operator

class PortScanner( object ):
	def __init__( self ):
		self.ranges = [ range( 1, 1024 ) ]
		self.nThreads = 100
		
	def SetRange( self, *r ):
		self.ranges = [ range( *r ) ]

	def AddRange( self, *r ):
		self.ranges.append( range( *r ) )

class PortListener( threading.Thread ):
	def __init__( self, port ):
		threading.Thread.__init__( self )
		self.port = port
		self.setDaemon( 1 )
		self.output = sys.stdout
		
	def run( self ):
		s = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
		try:
			s.bind( ( '', self.port ) )
			s.listen( 1 )
			while 1:
				conn, addr = s.accept()
				self.output.write( 'Received connection on %d from %s.\n' % ( self.port, str( addr ) ) )
				conn.close()
		except socket.error, e:
			if e[0] == 10048:
				self.output.write( 'Cannot listen on port %d: Address already in use.\n' % self.port )
			else: raise

class PortRangeListener( object ):
	def __init__( self ):
		self.ranges = [ range( 1, 1024 ) ]

	def Listen( self ):
		ports = reduce( operator.add, self.ranges )
		ports.sort()
		self.threads = map( PortListener, ports )
		map( lambda t: t.start(), self.threads )
		