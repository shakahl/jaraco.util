import htmllib, formatter
import logging

log = logging.getLogger( 'TableParser' )

class TableParser( htmllib.HTMLParser ):
	def __init__( self ):
		#raise Exception, 'The table parser doesn\'t work right now'
		htmllib.HTMLParser.__init__( self, formatter.NullFormatter() )

	def feed( self, string ):
		self.tables = []
		htmllib.HTMLParser.feed( self, string )
		
	def start_table( self, attrs ):
		self.currentTable = []
		self.extraRows = {}

	def end_table( self ):
		if self.currentTable:
			self.tables.append( self.currentTable )
		del self.currentTable, self.extraRows

	def start_tr( self, attrs ):
		# implicitly do </tr> if <tr> is found nested.
		if hasattr( self, 'currentRow' ):
			self.end_tr( )
		self.currentRow = []
		self.currentColumnNumber = 0

	def end_tr( self ):
		if hasattr( self, 'currentRow' ):
			if self.currentRow:
				self.currentTable.append( self.currentRow )
			del self.currentRow, self.currentColumnNumber
		# else ignore </tr> because no preceding <tr> was found

	def start_td( self, attrs ):
		self.checkForExtraRows()
		attrs = dict( attrs )
		try:
			# TODO: assign for additional columns as well if 'colspan' is set
			self.extraRows[ self.currentColumnNumber ] = int(attrs['rowspan']) - 1
		except KeyError:
			pass
		try:
		    self.extraCols = int(attrs['colspan']) - 1
		except KeyError:
			self.extraCols = 0
		# start remembering the contents here
		self.save_bgn()

	def end_td( self ):
		# if self.value has been set (by something like an href),
		#  use it.  Otherwise, just use the text.
		try:
			self.currentRow.append( self.value )
			del self.value
		except AttributeError:
			self.currentRow.append( self.save_end() )
		self.currentRow.extend( [''] * self.extraCols )
		self.currentColumnNumber += 1

	# note that this will not be called if the extra rows are in the last column(s).
	def checkForExtraRows( self ):
		log.debug( 'self.extraRows is %s.', self.extraRows )
		log.debug( 'currentColumnNumber is %s.', self.currentColumnNumber )
		if self.extraRows.has_key( self.currentColumnNumber ):
			self.extraRows[ self.currentColumnNumber ] -= 1
			self.currentRow.append( '' )
			if self.extraRows[ self.currentColumnNumber ] == 0:
				del self.extraRows[ self.currentColumnNumber ]
			# Now increment the column number and check again
			self.currentColumnNumber += 1
			self.checkForExtraRows()
