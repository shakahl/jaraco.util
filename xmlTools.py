import tools, itertools
import xml.dom.minidom
import string

import logging
log = logging.getLogger( __name__ )

quoteSubstitutions = ( ('"','&quot;'),
# leave out this substitution for now
#					   ("'",'&apos;')
					   )
reverseSubstitutions = tools.ReverseLists( quoteSubstitutions )

def ToXMLQuotedString( s ):
	return tools.ReplaceList( s, quoteSubstitutions )

def FromXMLQuotedString( s ):
	return tools.ReplaceList( s, reverseSubstitutions )

def GetXMLRepresentation( value ):
	"Get the appropriate XML representation for value"
	try:
		value = value.XMLRepr
	except AttributeError: pass
	# want to get the best precision for a float
	if isinstance( value, float ):
		value = repr( value )
	else:
		value = ToXMLQuotedString( value )
	return value

from datetime import datetime, date, time
from time import strptime
def ParseXMLTime( xmlTime ):
	"Take a time string in XML format and return the value as a datetime object"
	pattern = '%Y-%m-%dT%H:%M:%S'
	return datetime( *strptime( xmlTime, pattern )[:6] )

class XMLObject( dict ):
	xml = xml.dom.minidom.getDOMImplementation()
	
	def XMLRepr( self ):
		nodeName = self.encodeXMLName( self.__class__.__name__ )
		element = self.xml.createDocument( '', nodeName, '' ).documentElement
		for attr in self.getAttributes( ):
			element.setAttribute( *attr )
		return element.toxml()
			

	def getAttributes( self ):
		return itertools.imap( self.encodeAttribute, self.iteritems() )

	def encodeAttribute( self, (name,val) ):
		if type( val ) in ( datetime, date, time ):
			val = val.isoformat()
		return ( self.encodeXMLName( name ), str( val ) )

	def encodeXMLName( self, n ):
		return string.join( self.encodeXMLNameChars( n ), '' )

	validChars = range( 0x30, 0x3A ) + range( 0x41, 0x5B ) + range( 0x61, 0x7B ) + [ ord( '-' ), ord( '_' ), ord( '.' ) ]
	def encodeXMLNameChars( self, n ):
		for c in n:
			if ord( c ) in self.validChars:
				yield c
			else:
				yield '_x%04x_' % ord( c )

def loadXMLObjects( filename, objectModule ):
	doc = xml.dom.minidom.parse( open( filename, 'r' ) )
	return getXMLObjects( doc.getElementsByTagName( '*' ), objectModule )

def getXMLObjects( nodeSet, objectModule ):
	for objectNode in nodeSet:
		try:
			objectClass = getattr( objectModule, objectNode.nodeName )
			yield objectClass( objectNode.attributes.items() )
		except AttributeError: pass # class does not exist

def getChildrenByType( node, type ):
	return filter( lambda n: n.nodeType == type, node.childNodes )

def getChildElements( node ):
	return getChildrenByType( node, node.ELEMENT_NODE )