# -*- coding: UTF-8 -*-

"""ProxyTunnel.py
This modules defines classes to override proxy functionality on Python
2.3 due to its limitation (non-support) of https via a proxy server.

Copyright © 2004 Sandia National Laboratories

This module uses the tunnel method to traverse a proxy.  It first connects
to the proxy server via HTTP, and requests a tunnel via the CONNECT
command.

Once the connect succeeds, the handler sets the .sock attribute of the
request to the socket of the tunnel, which can then be used to establish
an HTTP or HTTPS connection to the other end of the tunnel.
"""

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Rev: 5 $'[6:-2]
__svnauthor__ = '$Author: Jaraco $'[9:-2]
__date__ = '$Date: 04-06-23 12:27 $'[7:-2]

import httplib, urllib2, urllib, socket
import autohttp

class TunnelResponse( httplib.HTTPResponse ):
	def _check_close( self ):
		# assume it will not close
		# I don't know under what conditions the proxy will deny a connection.
		# It seems the Sandia proxy always allows the connection.
		return False

	def begin( self ):
		# HTTPResponse always assumes the connection will close unless
		#  the response is chunked or length is not None, both of which are
		#  not true in the tunnel case... so override the will_close value.
		httplib.HTTPResponse.begin( self )
		self.will_close = False

class HTTPSConnectionEstablished( httplib.HTTPSConnection ):
	"""HTTPS Connection class, identical to httplib version except an already
	established link may be used."""
	def connect( self, sock = None ):
		if not sock:
			httplib.HTTPSConnection.connect( self )
		else:
			ssl = httplib.socket.ssl( sock, self.key_file, self.cert_file )
			self.sock = httplib.FakeSocket( sock, ssl )

class HTTPSHandler( autohttp.HTTPSHandler ):
	def https_open( self, req ):
		return self.do_open( HTTPSConnectionEstablished, req )

class ProxyTunnelHandler( urllib2.ProxyHandler ):
	def https_open( self, request ):
		proxy = urllib2.urlparse.urlparse( self.proxies['http'] )[1]
		tunnel_connection = httplib.HTTPConnection( proxy )
		tunnel_connection.response_class = TunnelResponse
		host_port = urllib.splitnport( request.get_host(), httplib.HTTPS_PORT )
		tunnel_connection.putrequest( 'CONNECT', '%s:%d' % host_port )
		# httplib will attempt to connect() here.  be prepared
		# to convert a socket error to a URLError.
		try:
			tunnel_connection.endheaders()
		except socket.error, err:
			raise urllib2.URLError(err)
		response = tunnel_connection.getresponse()
		response.read()
		request.sock = tunnel_connection.sock
		
		# return None so other handlers will handle the modified request

def test():
	o = urllib2.build_opener( ProxyTunnelHandler( {'http':'http://sonproxy.sandia.gov:80'} ),
							  HTTPSHandler, autohttp.HTTPHandler ) 
	urllib2.install_opener( o )
	return urllib2.urlopen( 'https://www.jaraco.com:444/' )
	
	