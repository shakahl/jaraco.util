# -*- coding: UTF-8 -*-

"""Universal
	Draft functionality to create an universal EnvMon translator
that is entirely data-driven.
	
Copyright © 2004 Sandia National Laboratories  
"""

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Revision: 3 $a'[11:-2]
__vssauthor__ = '$Author: Jaraco $'[9:-2]
__date__ = '$Modtime: 04-06-23 12:31 $'[10:-2]

import os, logging
import win32com.client, win32con

log = logging.getLogger( 'Universal Translator' )

xmldirectory = r'\\megaload\home\jaraco\my documents\my projects\Data Collection Toolset'
t1file = os.path.join( xmldirectory, 'T-1.xml' )

class translator( object ):
	def __init__( self, definitionFilename ):
		definition = win32com.client.Dispatch( 'Msxml2.DOMDocument.4.0' )
		definition.setProperty( 'NewParser', True )
		definition.setProperty( 'SelectionNamespaces',
								'xmlns:em="urn:envmon.mms.sandia.gov:envmon"' )
		definition.load( definitionFilename )
		self.result = self.processNode( definition.documentElement )

	def handleEnvMonChild( self, parent, child ):
		if self.isEnvMonNode( child ):
			parent.appendChild( child )
		elif self.isAttributeNode( child ):
			parent.addAttribute( child.getAttribute( 'Name' ), child.Value )
			
	def isEnvMonNode( node ):
		return node.prefix == 'em'
	isEnvMonNode = staticmethod( isEnvMonNode )
	
	def getChildResults( self, node, contextData ):
		for childNode in node.childNodes:
			yield self.processNode( childNode, contextData )

	def processNode( self, node, contextData = None ):
		log.debug( 'Processing node %s.', node.nodeName )
		if translator.isEnvMonNode( node ):
			# create a newNode, a clone of the current node
			cloneChildren = False
			newNode = node.cloneNode( cloneChildren )
			# iterate through results for children nodes
			results = self.getChildResults( node, contextData )
			for result in results:
				self.handleEnvMonChild( parent = newNode, child = result )
			result = newNode
		else:
			# do any actions pertinent to children, should call getChildResults
			result = self._processDCNode( node, contextData )
		return result

	def _processDCNode( self, node, contextData ):
		methodName = 'handle%sNode' % node.nodeName
		try:
			method = getattr( self, methodName )
			result = method( node, contextData )
		except AttributeError:
			log.error( 'Unknown node %s found. Ignoring' % node.nodeName )
			# iterate through results for children nodes
			result = tuple( self.getChildResults( node, contextData ) )
		return result

	# handle<NodeName>Node functions should take the node and contextData as parameters,
	#  and return the tuple( result, contextData ) where result is dependent on the node and
	#  contextData is the new context data (may be the original object passed).

	def handleMethodNode( self, node, contextData ):
		"""
		Method nodes describe a method by which data is collected.
		Since there are many classes of method nodes, each is represented
		by a class in code.
		Since a method collects data, the contextData should be altered by this
		method.
		"""
		className = '%sMethod' % node.getAttribute( 'class' )
		c = globals()[ className ]
		method = c( node )
		doMethodChildren = lambda data: self.getChildResults( node, data )
		results = map( doMethodChildren, method.Run() )
		return results

#	def processStringNode( self, node, contextData ):
#		attributes = map( lambda a: (a.name, a.value), node.attributes )
#		attributes = dict( attributes )
#		if not attributes['minLength'] <= len( contextData ) <= attributes['maxLength']:
#			raise ValueError, 'String not within bounds'

	def handleAttributeNode( self, node, contextData ):
		result = {}
		result['Value'] = self.getChildResults( node, contextData )
		if isinstance( result['Value'], ( tuple, list ) ):
			raise NotImplementedError, 'attributes must have only one value'
		result['Name'] = node.getAttribute( 'Name' )
		return result

	def handleValueNode( self, node, contextData ):
		length = node.getAttribute( 'length' )
		value = contextData.getBytes( length )
		self.getChildResults( node, value )
		return value

class ContextData( object ):
	def __init__( self, value ):
		self.value = value
		self.position = 0

	def getBytes( self, q ):
		p = self.position
		result = self.value[ p: p + q ]
		self.position += q
		return result

class Method( object ):
	def __init__( self, node ):
		attributes = map( lambda a: (a.name, a.value), node.attributes )
		self.__dict__.update( dict( attributes ) )

class FileMethod( Method ):
	def __init__( self, *args ):
		super( self.__class__, self ).__init__( *args )

	def Run( self ):
		return ( open( self.filename, 'r' ), )

import win32file
class RS232Method( Method ):
	sampleMessages = ['qiMAAAAGH5EAABgADCDAAB8ABAMBBAUTQAcgAAAAAAAAAAC1mw==\n', 'qiUAAAAGH5EAABkADCDAAB8AAgMBBAUTQkEg/3oAAAAAAAAAAKA1\n', 'qiMAAAAGH5EAABoADSDAAB8ABAIBBAUTRQcgAAAAAAAAAAB60g==\n', 'qiMAAAAGH5EAABsADiDAAB8ABAMBBAUTRVAgAAAAAAAAAADCKQ==\n', 'qiMAAAAGJf4AABcADCDAAB8ABAYBBAUUECMgAAAAAAAAAABu8w==\n', 'qiMAAAAGH5EAABwADyDAAB8ABAIBBAUTUQIgAAAAAAAAAAD7Vw==\n', 'qiMAAAAGJf4AABgADSDAAB8ABAIBBAUUFDUgAAAAAAAAAAD4iw==\n', 'qiMAAAAGGcoAAB0ADCDAAB8ABAYBBAUUB0EgAAAAAAAAAAA8rg==\n', 'qiMAAAAGGcoAAB4ADSDAAB8ABAIBBAUUCBMgAAAAAAAAAACkng==\n', 'qiMAAAAGPbsAAA8AByDAAB8ABAYBBAUSGAkgAAAAAAAAAADBOg==\n']
	def __init__( self, *args ):
		super( self.__class__, self ).__init__( *args )
		# for now don't self.setupCOMM( )

	def Run( self ):
		result = map( lambda s: s.decode( 'base64' ), self.sampleMessages )
		return result
		"""
		while( 1 ):
			hr, result = win32file.ReadFile( hCom, 512, None )
			yield result
		"""

	def setupCOMM( self ):
		self.hCom = win32file.CreateFile( self.port,
									 win32con.GENERIC_READ | win32con.GENERIC_WRITE,
									 0,
									 None,
									 win32con.OPEN_EXISTING,
									 0,
									 0 )
		dcb = win32file.GetCommState( self.hCom )
		baudRateConstant = 'CBR_%s' % self.baud
		baudRate = getattr( win32con, baudRateConstant )
		dcb.BaudRate = baudRate
		dcb.ByteSize = 8
		dcb.Parity = win32con.NOPARITY
		dcb.StopBits = win32con.ONESTOPBIT
		win32file.SetCommState( self.hCom, dcb )

