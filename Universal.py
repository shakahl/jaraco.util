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
		self.createResultDocument()
		self.processNode( definition.documentElement )

	def createResultDocument( self ):
		self.result = win32com.client.Dispatch( 'Msxml2.DOMDocument.4.0' )
		self.result.documentElement = \
			self.result.createNode( win32com.client.constants.NODE_ELEMENT, 'result', 'el' )
		self.currentResultNode = self.result.documentElement

	def processNode( self, node, contextData = None ):
		log.info( 'Processing node %s', node.nodeName )
		# unless overridden, feed the same data to children as fed in
		newContextDataFeed = ( contextData, )
		if node.prefix:
			# this is not a data collection object, so copy it
			cloneChildren = False
			clonedNode = node.cloneNode( cloneChildren )
			self.currentResultNode.appendChild( clonedNode )
			previousNode = self.currentResultNode
			self.currentResultNode = clonedNode
		else:
			methodName = 'process%sNode' % node.nodeName
			try:
				method = getattr( self, methodName )
				result = method( node, contextData )
				if not result is None:
					newContextDataFeed = result
			except AttributeError:
				log.error( 'Unknown node %s found. Ignoring' % node.nodeName )
			previousNode = self.currentResultNode
		log.debug( 'newContextDataFeed is %s', newContextDataFeed )
		for contextData in newContextDataFeed:
			for child in node.selectNodes( '*' ):
				self.processNode( child, contextData )
		self.currentResultNode = previousNode

	def processDataCollectionNode( self, node, contextData ):
		pass

	def processMethodNode( self, node, contextData ):
		"""
		Method nodes describe a method by which data is collected.
		Since there are many classes of method nodes, each is represented
		by a class in code.
		"""
		className = '%sMethod' % node.getAttribute( 'class' )
		c = globals()[ className ]
		method = c( node )
		return method.Run()

	def processStringNode( self, node, contextData ):
		attributes = map( lambda a: (a.name, a.value), node.attributes )
		attributes = dict( attributes )
		if not attributes['minLength'] <= len( contextData ) <= attributes['maxLength']:
			raise ValueError, 'String not within bounds'

	def processAttributeNode( self, node, contextData ):
		value = self.processNode( node.getSingleNode( '*' ) )
		name = node.getAttribute( 'Name' )
		self.currentResultNode.setAttribute( name, value )

	def processCheckNode( self, node, contextData ):
		pass #stubbed

	def processFieldNode( self, node, contextData ):
		length = node.getAttribute( 'length' )
		return contextData[:length]

class ContextData( object ):
	def __init__( self, value ):
		self.value = value

	def getNext( self, q ):
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
		result = map( ContextData, result )
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

