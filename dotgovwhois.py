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
__version__ = '$Rev:  $'[6:-2]
__svnauthor__ = '$Author:  $'[9:-2]
__date__ = '$Date:  $'[7:-2]

import cookielib, urllib2, os, re
from ClientForm import ParseResponse

def init( ):
	"""Initialize HTTP functionality to support cookies, which are necessary
	to use the HTTP interface."""
	cj = cookielib.CookieJar()
	opener = urllib2.build_opener( urllib2.HTTPCookieProcessor(cj) )
	urllib2.install_opener( opener )

def doQuery( query ):
	"Perform an whois query on the dotgov server."
	url = urllib2.urlopen( 'http://dotgov.gov/whois.aspx' )
	forms = ParseResponse( url )
	assert len( forms ) == 1
	form = forms[0]
	if form.attrs['action'] == 'agree.aspx':
		# we've been redirected to a different form
		# need to agree to license agreement
		Agree( form )
		# note this could get to an infinite loop if cookies aren't working
		# or for whatever reason we're always being redirected to the
		# agree.aspx page.
		return doQuery( query )
	form['who_search'] = query
	resp = urllib2.urlopen( forms[0].click() )
	return resp.read()

def Agree( form ):
	"agree to the dotgov agreement"
	agree_req = form.click()
	u2 = urllib2.urlopen( agree_req )
	resp = u2.read()

from htmllib import HTMLParser
from formatter import NullFormatter, DumbWriter, AbstractFormatter
class dotgovparser( HTMLParser ):
	def __init__( self, writer ):
		self.__formatter__ = AbstractFormatter( writer )
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
		try:
			response = doQuery( query )
		except urllib2.URLError:
			self.wfile.write( 'Could not contact whois HTTP service.\n' )
			return
		# fix the response; the parser doesn't understand tags that have a slash
		# immediately following the tag name
		# Alternatively, one could use tidylib with 'drop-empty-paras' set to False
		# response = str( tidy.parseString( response, drop_empty_paras = False ) )
		response = re.sub( r'<(\w+)/>', r'<\1 />', response )
		writer = MyWriter( self.wfile )
		dotgovparser( writer ).feed( response )

class Listener( TCPServer, ThreadingMixIn ):
	def __init__( self ):
		TCPServer.__init__( self, ( '', 43 ), Handler )

if __name__ == '__main__':
	init()
	l = Listener()
	l.serve_forever()