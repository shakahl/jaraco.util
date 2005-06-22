# -*- coding: UTF-8 -*-

""" autohttp
	Tools for automating http processes.
	
Copyright © 2004 Sandia National Laboratories  
"""

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Rev$'[6:-2]
__svnauthor__ = '$Author$'[9:-2]
__date__ = '$Date$'[7:-2]

import httplib, mimetypes
from urlparse import urlparse, urlunparse, urljoin
import urllib, urllib2, htmllib, formatter, socket
import string, re, logging, time, os
import cookies, tools

log = logging.getLogger( 'autohttp' )

def splitHostPort( host ):
	try:
		host, port = string.split( host, ':' )
		port = int( port )
	except ValueError:
		port = None
	return host, port

class RequestMatch( object ):
	"An object that when called will return true of the cookie matches the request"
	def __init__( self, request ):
		self.request = request

	def __call__( self, cookie ):		
		"Return true if the given cookie matches this request"
		r = self.request
		host, port = splitHostPort( r.get_host() )
		selector = r.get_selector()
		scheme = r.get_type()
		result = True
		if cookie.get( 'domain', host ) not in host:
			result = False
		if cookie.get( 'path', selector ) not in selector:
			result = False
		if cookie.isSecure() and not scheme == 'https':
			result = False
		return result
		
class CookieHandler( urllib2.BaseHandler ):
	"""This handler will ensure that on a redirect, any cookies in the redirect request
	will be processed.  Normally, the OpenerDirector is responsible for handling
	information such as this, but an OpenerDirector never sees a redirect request
	if the HTTPRedirectHandler is installed."""
	handler_order = 50
	def http_error_302( self, req, fp, code, msg, headers ):
		self.parent.processCookies( headers )
	http_error_301 = http_error_303 = http_error_307 = http_error_302
		
class AbstractHTTPHandler( object ):
	# override do_open because the default one uses deprecated HTTP
	#  class
	def do_open(self, http_class, req):
		host = req.get_host()
		if not host:
			raise URLError('no host given')

		connection = http_class( host ) # will parse host:port
		# if the request has a socket attached to it, use it explicitly.
		if hasattr( req, 'sock' ):
			connection.connect( req.sock )
		if req.has_data():
			method = 'POST'
			if 'Content-Type' not in req.headers:
				req.add_header( 'Content-Type', 'application/x-www-form-urlencoded' )
		else:
			method = 'GET'
		connection.request( method,
							req.get_selector(),
							req.get_data(),
							headers=req.headers )

		response = connection.getresponse()
		code, msg, hdrs = response.status, response.reason, response.msg
		fp = response.fp
		if code == 200:
			return response
		else:
			return self.parent.error(req.get_type(), req, fp, code, msg, hdrs )

class HTTPHandler( AbstractHTTPHandler, urllib2.HTTPHandler ):
	def http_open( self, req ):
		return self.do_open( httplib.HTTPConnection, req )
	
class HTTPSHandler( AbstractHTTPHandler, urllib2.HTTPSHandler ):
	def https_open( self, req ):
		return self.do_open( httplib.HTTPSConnection, req )

opener = urllib2.build_opener( HTTPHandler, HTTPSHandler )
urllib2.install_opener( opener )

class MultipartHandler( object ):
	"A mix-in object for a Request for handling multi-part forms"
	boundary = '-'*10 + '$boundary'+hex( int( time.time() ) )
	def encode_multipart_formdata( self, fields, files ):
		"""
		fields is a sequence of (name, value) elements for regular form fields.
		files is a sequence of (name, filename, value) elements for data to be uploaded as files
		"""
		if isinstance( fields, dict ):
			fields = fields.items()
		self.lines = []
		map( self._get_field_lines, fields )
		map( self._get_filename_lines, files )
		self.lines.append( '--%s--' % self.boundary )
		self.lines.append( '' )
		CRLF = '\r\n'
		self.add_data( CRLF.join( self.lines ) )
		del self.lines
		content_type = 'multipart/form-data; boundary=%s' % self.boundary
		self.add_header( 'Content-Type', content_type )
	
	def _get_field_lines( self, ( key, value ) ):
		self.lines.append( '--' + self.boundary )
		self.lines.append( 'Content-Disposition: form-data; name="%s"' % key)
		self.lines.append( '' )
		self.lines.append( value )

	def _get_filename_lines( self, ( key, filename, value ) ):		
		self.lines.append( '--' + self.boundary )
		self.lines.append( 'Content-Disposition: form-data; name="%s"; filename="%s"' % ( key, filename ) )
		self.lines.append( 'Content-Type: %s' % self.get_content_type( filename ) )
		self.lines.append( '' )
		self.lines.append( value )

	def get_content_type( self, filename ):
		return mimetypes.guess_type( filename )[0] or 'application/octet-stream'

# by default, IE uses these headers
IE_default_headers = {
	'Accept': 'image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, application/x-shockwave-flash, application/vnd.ms-excel, application/vnd.ms-powerpoint, application/msword, */*',
	'Accept-Language': 'en-us',
	'Accept-Encoding': 'gzip, deflate',
	'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; .NET CLR 1.1.4322)',
	'Cache-Control': 'no-cache',
	'Connection': 'Keep-Alive'
	}

Mozilla_default_headers = {
	'Accept': 'text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,image/jpeg,image/gif;q=0.2,*/*;q=0.1',
	'Accept-Language': 'en-us,en;q=0.5',
	'Accept-Encoding': 'gzip,deflate',
	'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.5) Gecko/20031007',
	'Connection': 'Keep-Alive',
	'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'
	}

def getRelativeURL( targetURL, originalURL ):
	"Takes the relative URL passed and returns an absolute URL based on the original URL"
	return urljoin( originalURL, targetURL )

class FormField( dict ): pass

class FormParser( htmllib.HTMLParser ):
	def __init__( self ):
		htmllib.HTMLParser.__init__( self, formatter.NullFormatter() )
		self.fields = {}

	def start_form( self, attributes ):
		self.formAttributes = dict( attributes )

	def do_input( self, attributes ):
		"handle the <input> tag"
		field = FormField( dict( attributes ) )
		try:
			self.fields[ field['name'] ] = field
		except KeyError:
			# the field doesn't have a name, so ignore it
			pass
		if string.lower( field.get( 'type', 'text' ) ) == 'image':
			self.fields[ 'x' ] = FormField( { 'name': 'x', 'value': '0' } )
			self.fields[ 'y' ] = FormField( { 'name': 'y', 'value': '0' } )

	def start_textarea( self, attributes ):
		"handle the <textarea> tag"
		field = FormField( dict( attributes ) )
		self.fields[ field['name'] ] = field
		self.currentField = field
		self.save_bgn()

	def end_textarea( self ):
		value = self.save_end()
		self.currentField['value'] = value
		del self.currentField

class FormProcessor( object ):
	"""Proccesses an HTML Form in an automated fashion
	Call in this manner:
	>>> f = FormProcessor()
	>>> f.loadForm( 'http://www.mysite.org/path' )
	Then set the form fields that you want filled in.
	>>> f.submit()
	After doing this, f will have a submission object which is an HTTPConnection
	which has posted the form results.
"""
	def loadForm( self, request=None ):
		if not request:
			request = urllib2.Request( self.FormURL )
		self.formResponse = urllib2.urlopen( request )
		formFile = self.formResponse.read()
		log.debug( 'Successfully read form file' )
		self.formParser = FormParser()
		self.formParser.feed( formFile )
		self.formFields = dict( self.formParser.fields )

	def setFormField( self, name, value ):
		self.formFields[name]['value'] = value
		if string.lower( self.formFields[name].get( 'type', '' ) ) == 'hidden':
			log.warning( 'Overriding a hidden input value (%(name)s=%(value)s)' % self.formFields[name] )

	def buildSubmissionRequest( self, action = None, headers = {} ):
		"Submit the form.  Action overrides the default action specified in the form"
		data = {}
		log.debug( 'Form fields are: %s', self.formFields )
		for field in self.formFields.values():
			if string.lower( field.get( 'type', '' ) ) in ( 'reset', 'checkbox' ): continue
			data[field['name']] = field.get( 'value', '' )
		log.debug( 'Data before posted are: %s', data )
		assert string.lower( self.formParser.formAttributes['method'] ) == 'post'
		if not action:
			action = self.formParser.formAttributes['action']
		actionURL = getRelativeURL( action, self.FormURL )
		log.debug( 'Headers in form response were %s', self.formResponse.msg.headers )
		submissionRequest = urllib2.Request( actionURL, headers = headers )
		submissionRequest.add_header( 'Referer', self.FormURL )
		if self.formParser.formAttributes.get( 'enctype', '' ) == 'multipart/form-data':
			submissionRequest.encode_multipart_formdata( data )
		else:
			submissionRequest.add_data( urllib.urlencode( data ) )
		return submissionRequest

	def submit( self ):
		request = self.buildSubmissionRequest()
		return urllib2.urlopen( request )

class SessionOpenerDirector( urllib2.OpenerDirector ):
	"""A class that manages cookies (and thus sessions)"""
	def __init__( self ):
		urllib2.OpenerDirector.__init__( self )
		self.reset()

	def reset( self ):
		self._cookies = cookies.Container()

	def open( self, request, data = None ):
		if isinstance( request, str ):
			request = urllib2.Request( request )
		cookieHeader = self.getCookieHeader( request )
		if cookieHeader:
			request.add_header( 'Cookie', self.getCookieHeader( request ) )
			log.debug( 'Cookie: %s', cookieHeader )
		response = urllib2.OpenerDirector.open( self, request, data )
		path = urlparse( request.get_full_url() )[2]
		self.processCookies( response, path )
		return response

	def processCookies( self, response, path ):
		self._cookies.add( cookies.getCookies( response, path ) )

	def getCookieHeader( self, request ):
		return self._cookies.get_request_header( RequestMatch( request ) )

session_opener = SessionOpenerDirector()
map( session_opener.add_handler, ( urllib2.ProxyHandler(),
						   urllib2.HTTPDefaultErrorHandler(),
						   urllib2.HTTPRedirectHandler(),
						   HTTPHandler(), HTTPSHandler(),
						   CookieHandler() ) )
# To use the session opener, run the following:
#  urllib2.install_opener( session_opener )

# The following classes are in used for testing the request of
#  the above classes.
import SocketServer, sys
class echoHandler( SocketServer.StreamRequestHandler ):
	def handle( self ):
		from email.Parser import Parser
		# read the request line
		request = self.rfile.readline()
		sys.stdout.write( request )
		# use the e-mail class to read out the headers
		msg = Parser().parse( self.rfile, headersonly = True )
		# read out any data in the request
		if msg.has_key( 'Content-Length' ):
			msg.set_payload( self.rfile.read( int( msg['Content-Length'] ) ) )
		sys.stdout.write( msg.as_string() )
		sys.stdout.write( '\n***\n' )
		
class submissionTester( SocketServer.TCPServer ):
	def __init__( self, port = 80 ):
		SocketServer.TCPServer.__init__( self, ( '', port ), echoHandler )

def logRequest( log, request ):
	log.info( 'Requesting %s from %s.', request.get_selector(), request.get_host() )
	log.debug( 'Headers are %s', request.headers )
	log.debug( 'Data is %s', request.get_data() )