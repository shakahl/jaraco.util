# webtools.py
#  classes for supporting web processing
import string, re

# This class should only be instanciated within an ASP session.
class ASPForm( dict ):
	"""ASPForm
	Implements the ASP Request.Form object as a dictionary."""
	def __init__( self, Request ):
		self.Request = Request
		self._LoadForm()
		
	def _GetASPFormElements( self ):
		for field in self.Request.Form:
			yield ( field, self.Request.Form( field) () )
			
	def _LoadForm( self ):
		self.update( dict( self._GetASPFormElements() ) )

	def GetFormFields( self ):
		return self.keys()

	def GetFormValues( self ):
		return self.values()

	def __str__( self ):
		return string.join( map( lambda x: '%s: %s\n' % x, self.items() ), '' )

class Validator( object ):
	def __init__( self, expression, message ):
		self.__dict__.update( vars() ); del self.__dict__['self']

	def Validate( self, field, value ):
		matcher = re.match( self.expression, value )
		if not matcher:
			return self.message % vars()

def getCGIFieldStorage( Request ):
	"""Take an ASP Request and parse it as a cgi.FieldStorage object.
This is particularly useful when processing multipart/formdata forms, which
ASP balks on"""
	import cgi
	from StringIO import StringIO
	environ = {}
	for key in Request.ServerVariables:
		environ[key] = str( Request.ServerVariables[key] )
	return cgi.FieldStorage( StringIO( res ), environ = environ )
		