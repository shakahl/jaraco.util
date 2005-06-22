#! -*- coding: UTF-8 -*-

"""dotgovwhois.py

HTTP scraper for dotgov.gov whois service (currently web only).

Run the script from the command line and it will service port 43 as a whois server,
passing the query to the web form and parsing the results into a textual format.

Security Evaluation
There should be no security issues with running this service, as this service merely passes
the query directly on to the dotgov HTTP service.  There are no opportunities for buffer overflow
unless issues exist in StreamRequestHandler rfile object.

Copyright © 2005 Sandia National Laboratories  
"""

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Rev$'[6:-2]
__svnauthor__ = '$Author$'[9:-2]
__date__ = '$Date$'[7:-2]

import urllib2, os, re
from ClientForm import ParseResponse, ItemNotFoundError
from htmllib import HTMLParser
from formatter import NullFormatter, DumbWriter, AbstractFormatter

try:
	raise ImportError
	import cookielib
	urlopen = urllib2.urlopen
except ImportError:
	from ClientCookie import urlopen

def init( ):
	"""Initialize HTTP functionality to support cookies, which are necessary
	to use the HTTP interface."""
	try:
		cj = cookielib.CookieJar()
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor(cj) )
		urllib2.install_opener( opener )
	except NameError:
		pass

def GetHandler( query ):
	if re.search( r'\.ar$', query.lower() ): return doARQuery, ARParser
	if re.search( r'(\.fed\.us|\.gov)$', query.lower() ): return doGovQuery, GovParser

class WhoisHandler( object ):
	"""WhoisHandler is an abstract class for defining whois interfaces for
	web-based nic servers.
	Child classes must define a 'services' attribute which is a regular expression
	that will match domains serviced by that handler.
	Also, child classes must define LoadHTTP which will retrieve the HTTP response
	and a _parser class which is an HTMLParser capable of parsing the response and
	outputting the textual result."""
	def __init__( self, query = None ):
		self._query = query

	def GetHandler( query ):
		"""Search through the global variables for WhoisHandlers and return the one
		that matches the query"""
		query = query.lower()
		handlers = filter( WhoisHandler._IsWhoisHandler_, globals().values() )
		matches = filter( lambda c: re.search( c.services, query ), handlers )
		if not len( matches ) == 1:
			if len( matches ) == 0: error = 'Domain for %s is not serviced by this server.'
			else: error = 'Server error, ambiguous nic server resolution for %s.'
			raise ValueError, error % query
		return matches[0]( query )
	GetHandler = staticmethod( GetHandler )

	def _IsWhoisHandler_( ob ):
		return hasattr( ob, '__bases__' ) and WhoisHandler in ob.__bases__
	_IsWhoisHandler_ = staticmethod( _IsWhoisHandler_ )

	def ParseResponse( self, s_out ):
		# fix the response; the parser doesn't understand tags that have a slash
		# immediately following the tag name (part of the XHTML 1.0 spec).
		# Alternatively, one could use tidylib with 'drop-empty-paras' set to False
		# response = str( tidy.parseString( response, drop_empty_paras = False ) )
		response = re.sub( r'<(\w+)/>', r'<\1 />', self._response )
		writer = MyWriter( s_out )
		self._parser( AbstractFormatter( writer ) ).feed( response )

class ArgentinaWhoisHandler( WhoisHandler ):
	services = r'\.ar$'
	
	def LoadHTTP( self ):
		query = self._query
		pageURL = 'http://www.nic.ar/consdom.html'
		form = ParseResponse( urlopen( pageURL ) )[0]
		form['nombre'] = query[ :query.find( '.' ) ]
		try:
			domain = query[ query.find( '.' ) : ]
			form['dominio'] = [ domain ]
		except ItemNotFoundError:
			raise ValueError, 'Invalid domain (%s)' % domain
		req = form.click()
		#req.data = 'nombre=%s&dominio=.com.ar' % query
		req.add_header( 'referer', pageURL )
		resp = urlopen( req )
		self._response = resp.read()

	class _parser( HTMLParser ):
		def start_tr( self, attrs ):
			pass # have to define this for end_tr to be called.
			
		def end_tr( self ):
			self.formatter.add_line_break()


class GovWhoisHandler( WhoisHandler ):
	services = r'(\.fed\.us|\.gov)$'
	def LoadHTTP( self ):
		query = self._query
		"Perform an whois query on the dotgov server."
		url = urlopen( 'http://dotgov.gov/whois.aspx' )
		forms = ParseResponse( url )
		assert len( forms ) == 1
		form = forms[0]
		if form.attrs['action'] == 'agree.aspx':
			# we've been redirected to a different form
			# need to agree to license agreement
			self.Agree( form )
			# note this could get to an infinite loop if cookies aren't working
			# or for whatever reason we're always being redirected to the
			# agree.aspx page.
			return self.LoadHTTP()
		form['who_search'] = query
		resp = urlopen( forms[0].click() )
		self._response = resp.read()

	def Agree( self, form ):
		"agree to the dotgov agreement"
		agree_req = form.click()
		u2 = urlopen( agree_req )
		resp = u2.read()

	class _parser( HTMLParser ):
		def __init__( self, formatter ):
			self.__formatter__ = formatter
			# Use the null formatter to start; we'll switch to the outputting
			#  formatter when we find the right point in the HTML.
			HTMLParser.__init__( self, NullFormatter() )
			
		def start_td( self, attrs ):
			attrs = dict( attrs )
			# I identify the important content by the tag with the ID 'TD1'.
			# When this tag is found, switch the formatter to begin outputting
			#  the response.
			if 'id' in attrs and attrs['id'] == 'TD1':
				self.formatter = self.__formatter__

		def end_td( self ):
			# switch back to the NullFormatter
			if not isinstance( self.formatter, NullFormatter ):
				self.formatter = NullFormatter( )

class MyWriter( DumbWriter ):
	def send_flowing_data( self, data ):
		# convert non-breaking spaces to regular spaces
		data = data.replace( '\xa0', ' ' )
		DumbWriter.send_flowing_data( self, data )
		
from SocketServer import TCPServer, ThreadingMixIn, BaseRequestHandler, StreamRequestHandler

class Handler( StreamRequestHandler ):
	def handle( self ):
		query = self.rfile.readline().strip()
		print self.client_address, 'requests', query
		handler = WhoisHandler.GetHandler( query )
		try:
			handler = WhoisHandler.GetHandler( query )
			handler.LoadHTTP()
			handler.ParseResponse( self.wfile )
			print self.client_address, 'success'
		except urllib2.URLError:
			self.wfile.write( 'Could not contact whois HTTP service.\n' )
		except ValueError, e:
			print e
			self.wfile.write( '%s\n' % e )

class Listener( ThreadingMixIn, TCPServer ):
	def __init__( self ):
		TCPServer.__init__( self, ( '', 43 ), Handler )

if __name__ == '__main__':
	init()
	l = Listener()
	l.serve_forever()