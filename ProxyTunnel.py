# stuff

import httplib, urllib2, urllib
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
			raise URLError(err)
		response = tunnel_connection.getresponse()
		response.read()
		request.sock = tunnel_connection.sock
		
		# return None so other handlers will handle the modified request

def test():
	o = urllib2.build_opener( ProxyTunnelHandler( {'http':'http://sonproxy.sandia.gov:80'} ),
							  HTTPSHandler, autohttp.HTTPHandler ) 
	urllib2.install_opener( o )
	return urllib2.urlopen( 'https://www.jaraco.com:444/' )
	
	