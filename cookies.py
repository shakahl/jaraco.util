import os, copy
import itertools
import string

class CookieMonster( object ):
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

	def makeCookie( self, Key, Value, Domain, Flags, ExpireLow, ExpireHigh, CreateLow, CreateHigh ):
		Expires = ( int( ExpireHigh ) << 32 ) | int( ExpireLow )
		Created = ( int( CreateHigh ) << 32 ) | int( CreateLow )
		del ExpireHigh, ExpireLow, CreateHigh, CreateLow
		Flags = int( Flags )
		cookie = vars()
		del cookie['self']
		return cookie


def isNotCookieDelimiter(s ):
	return s != '*\n'