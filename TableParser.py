import htmllib, formatter

class TableParser( htmllib.HTMLParser ):
	def __init__( self ):
		htmllib.HTMLParser.__init__( self, formatter.NullFormatter() )

	def feed( self, string ):
		self.tables = []
		htmllib.HTMLParser.feed( self, string )
		
	def start_table( self, attrs ):
		self.currentTable = []

	def end_table( self ):
		if self.currentTable:
			self.tables.append( self.currentTable )
		del self.currentTable

	def start_tr( self, attrs ):
		self.currentRow = []

	def end_tr( self ):
		if self.currentRow:
			self.currentTable.append( self.currentRow )
		del self.currentRow

	def start_td( self, attrs ):
		try:
		    self.extraCols = int(dict(attrs)['colspan']) - 1
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

