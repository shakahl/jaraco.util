# -*- coding: UTF-8 -*-

"""webtools
	Classes for supporting web data processing.
	
Copyright © 2004-2008 Jason R. Coombs
"""

__author__ = 'Jason R. Coombs <jaraco@jaraco.com>'
__version__ = '$Rev$'[6:-2]
__svnauthor__ = '$Author$'[9:-2]
__date__ = '$Date$'[7:-2]

import re, cgi
from logging import Handler, getLogger
log = getLogger( __file__ )

class FileWriter(object):
	"""A Python-style file object (with a .write method) that uses the supplied
	function to handle the writes.

	>>> w = FileWriter(Response.Write) #doctest:+SKIP
	>>> w.write('text') #doctest:+SKIP
	"""
	def __init__( self, handler ):
		self.__handler__ = handler

	def write( self, data ):
		self.__handler__( data )

class UploadError( RuntimeError ): pass

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
		return ''.join( map( lambda x: '%s: %s\n' % x, self.items() ) )

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
	try:
		data, bytesRead = Request.BinaryRead( bytes )
	except pythoncom.com_error, ( hr, msg, exc, arg ):
		if exc:
			wcode, source, text, helpFile, helpId, scode = exc
			# in IIS 6, there is a limit to the size of uploads.  If a file larger than
			#  the value specified in AspMaxRequestEntityAllowed is sent, BinaryRead
			#  will throw an exception with the scode set to 0x80004005.
			if scode == 0x80004005:
				raise UploadError, ('File size is too large', bytes )
		# anything that wasn't handled explicitly should be re-raised!
		raise
	if bytesRead != bytes:
		raise RuntimeError
	environ = {}
	for key in Request.ServerVariables:
		environ[key] = str( Request.ServerVariables[key] )
	return cgi.FieldStorage( StringIO( data ), environ = environ )

class ASPResponseHandler( Handler ):
	def __init__( self, ResponseObject, level = 0 ):
		Handler.__init__( self, level )
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

from xml.dom import minidom
class HTMLTable( object ):
	def __init__( self ):
		xml = minidom.getDOMImplementation()
		doc = xml.createDocument( None, 'root', None )
		self.element = doc.createElement( 'table' )

	def AddRow( self, seq, type='td' ):
		doc = self.element.ownerDocument
		row = doc.createElement( 'tr' )
		for col, arg in enumerate( seq ):
			elem = doc.createElement( type )
			if isinstance( arg, basestring ):
				arg = doc.createTextNode( arg )
			elem.appendChild( arg )
			row.appendChild( elem )
		self.element.appendChild( row )

	def AddHeaderRow( self, seq ):
		self.AddRow( seq, 'th' )

def HTMLLink( ref, s ):
	xml = minidom.getDOMImplementation()
	doc = xml.createDocument( None, 'root', None )
	elem = doc.createElement( 'a' )
	elem.setAttribute( 'href', ref )
	elem.appendChild( doc.createTextNode( s ) )
	return elem

import urllib2, ClientForm, cookielib

cj = cookielib.CookieJar()
cookie_handler = urllib2.HTTPCookieProcessor( cj )
default_opener = urllib2.build_opener( cookie_handler )

class PageGetter( object ):
	"set url to the target url or set request to the urllib2.Request object"
	def __init__( self, **attrs ):
		self.__dict__.update( attrs )
		self.__dict__.setdefault( '_opener', default_opener )

	def GetRequest( self ):
		req = getattr( self, 'request', None ) or urllib2.Request( getattr( self, 'url' ) )
		return req

	def Fetch( self ):
		return self._opener.open( self.GetRequest() )

	def Process( self ):
		resp = self.Fetch()
		forms = ClientForm.ParseResponse( resp )
		form = self.SelectForm( forms )
		self.FillForm( form )
		return form.click()

	def SelectForm( self, forms ):
		sel = getattr( self, 'form_selector', 0 )
		log.info( 'selecting form %s', sel )
		if not isinstance( sel, int ):
			# assume the selector is the name of the form
			forms = dict( map( lambda f: ( f.name, f ), forms ) )
		return forms[sel]

	def FillForm( self, form ):
		for name, value in self.form_items.items():
			if callable( value ):
				value = value()
			form[name] = value

	def __call__( self, next ):
		# process the form and set the request for the next object
		next.request = self.Process()
		return next

