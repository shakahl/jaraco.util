#

"cookies.py"

import os, copy, urllib
import itertools
import string, re

class CookieMonster( object ):
	"Read cookies out of a user's IE cookies file"
	def __init__( self, filename ):
		profileDir = os.environ['USERPROFILE']
		self.cookieDir = os.path.join( profileDir, 'Cookies' )
		self.cookieFile = file( os.path.join( self.cookieDir, filename ) )
		self.entries = self.getEntries( self.cookieFile )

	def getEntries( self, cookieFile ):
		while True:
			entry = itertools.takewhile( isNotCookieDelimiter, cookieFile )
			entry = map( string.rstrip, entry )
			if not entry: break
			cookie = self.makeCookie( *entry )
			yield cookie

	def makeCookie( self, key, value, domain, flags, ExpireLow, ExpireHigh, CreateLow, CreateHigh ):
		expires = ( int( ExpireHigh ) << 32 ) | int( ExpireLow )
		created = ( int( CreateHigh ) << 32 ) | int( CreateLow )
		del ExpireHigh, ExpireLow, CreateHigh, CreateLow
		flags = int( flags )
		domain, path = string.split( domain, '/', 1 )
		path = '/' + path
		cookie = vars()
		del cookie['self']
		return cookie


def isNotCookieDelimiter(s ):
	return s != '*\n'

class cookie( dict ):
	"""cookie class parses cookie information from HTTP Responses and outputs
	for HTTP Requests"""
	parameterNames = ( 'expires', 'path', 'domain', 'secure' )
	def __init__( self, header = None ):
		if header:
			self.readFromSetHeader( header )
			
	def readFromSetHeader( self, header ):
		'Read a cookie from a header as received in an HTTP Response'
		fields = re.split( ';\s*', header )
		splitEquals = lambda x: x.split( '=' )
		fieldPairs = map( splitEquals, fields )
		self.update( dict( fieldPairs ) )
		self.findName()

	def findName( self ):
		"Find the name of the cookie, which should be the only pair that's not a parameter"
		isNotParameter = lambda k: k not in self.parameterNames
		names = filter( isNotParameter, self )
		if not len( names ) == 1:
			raise ValueError, "Found more than one name/value pair where name isn't a cookie parameter"
		name = names[0]
		self['name'] = name
		self['value'] = self[name]
		del self[name]

	def getRequestHeader( self ):
		"returns the cookie as can be used in an HTTP Request"
		return '='.join( ( self['name'], urllib.quote( self['value'] ) ) )

	def isSecure( self ):
		return eval( string.capwords( self.get( 'secure', 'False' ) ) )