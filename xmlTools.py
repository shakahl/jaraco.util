# -*- coding: UTF-8 -*-

"""xmlTools
	Classes and routines for supporting xml processing.
	
Copyright © 2004 Sandia National Laboratories  
"""

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Revision: 6 $a'[11:-2]
__vssauthor__ = '$Author: Jaraco $'[9:-2]
__date__ = '$Modtime: 04-06-23 12:32 $'[10:-2]

import tools, itertools
import xml.dom.minidom
from xml.parsers.expat import ExpatError
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
		return self.getFragment().toxml()

	def _nodeName_( self ):
		return self.encodeXMLName( self.__class__.__name__ )
	_nodeName_ = property( _nodeName_ )

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

	def getFragment( self ):
		doc = self.xml.createDocument( None, 'root', None )
		element = doc.createElement( self._nodeName_ )
		for attr in self.getAttributes( ):
			element.setAttribute( *attr )
		return element

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

def saveXMLObjects( filename, objects, root = 'root' ):
	f = open( filename, 'a+' )
	try:
		doc = xml.dom.minidom.parse( f )
	except ExpatError:
		DOM = xml.dom.minidom.getDOMImplementation()
		doc = DOM.createDocument( None, root, None )
	xmlNodes = map( lambda o: o.getFragment(), objects )
	map( doc.documentElement.appendChild, xmlNodes )
	f.seek(0)
	f.write( doc.toprettyxml() )
	f.close()
	
	
	