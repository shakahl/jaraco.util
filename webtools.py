# webtools.py
#  classes for supporting web processing
import string, re, logging, cgi

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
ASP balks on.
The request must not have used the .Form member nor any of the form fields.
Additionally, the BinaryRead must not have been called yet.
"""
	from StringIO import StringIO
	bytes = Request.TotalBytes
	data, bytesRead = Request.BinaryRead( bytes )
	if bytesRead != bytes:
		raise RuntimeError
	environ = {}
	for key in Request.ServerVariables:
		environ[key] = str( Request.ServerVariables[key] )
	return cgi.FieldStorage( StringIO( data ), environ = environ )

class ASPResponseHandler( logging.Handler ):
	def __init__( self, ResponseObject, level = 0 ):
		logging.Handler.__init__( self, level )
		self.Response = ResponseObject
		self.Response.Write( '''<div id="log"><button onClick="log.style.display = 'none'">Clear Log</button><pre>\n''' )

	def emit( self, record ):
		s = self.format( record ) + '\n'
		s = cgi.escape( s )
		self.Response.Write( s )
		self.flush()

	def flush( self ):
		self.Response.Flush()

	def End( self ):
		self.Response.Write( '</pre></div>\n' )