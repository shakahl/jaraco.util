# Module SQL defines SQL routines and classes for an ODBC link to
#  SQL databases.

import types, time, string, re

# Currently, I use the odbc class included with Python.  Consider using
#  mxodbc or some other ODBC
from odbc import odbc
import dbi

# Time is a time object used to correctly handle time with respect
#  to SQL queries.  Ideally, this should be replaced by dbi.<some time object>
#  or the mxODBC equivalent.
class Time( object ):
	def __init__( self, value ):
		if type( value ) in ( types.TupleType, time.struct_time ):
			self.time = time.struct_time( value )
		elif type( value ) in ( types.FloatType, types.IntType, types.LongType ):
			self.time = time.gmtime( value )
		elif type( value ) is type( dbi.dbiDate(0) ):
			self.time = time.localtime( value )
		else:
			raise TypeError, 'Initialization value to Time must be a time tuple, dbiDate, or GMT seconds.'

	def _SQLRepr( self ):
		return time.strftime( "{ Ts '%Y-%m-%d %H:%M:%S' }", self.time )
	SQLRepr = property( _SQLRepr )	

	def __repr__( self ):
		return repr( self.time )
	
	def __str__( self ):
		return time.asctime( self.time )

	def __cmp__( self, other ):
		return cmp( self.time, other.time )

import re, operator
class Binary( str ):
	def _SQLRepr( self ):
		return '0x' + self.ASCII

	SQLRepr = property( _SQLRepr )
	
	def _GetASCIIRepresentation( self ):
		return string.join( map( lambda n: '%02x' % n, map( ord, self ) ), '' )

	ASCII = property( _GetASCIIRepresentation )

	def CreateFromASCIIRepresentation( s ):
		isHex = re.match( '(0x)?([0-9a-fA-F]*)$', s )
		if not isHex:
			raise ValueError, 'String is not hex characters'
		s = isHex.group(2)
		if not len( s ) % 2 == 0:
			raise ValueError, 'String must be of even length'
		bytes = re.findall( '(?s).{2}', s )
		toBin = lambda byteStr: chr( long( byteStr, 16 ) )
		return Binary( string.join( map( toBin, bytes ), '' ) )

	CreateFromASCIIRepresentation = staticmethod( CreateFromASCIIRepresentation )	

class Long( long ):
	def _SQLRepr( self ):
		# strip off the L at the end
		return long.__repr__( self )[:-1]
	SQLRepr = property( _SQLRepr )

class Database( object ):
	def __init__( self, ODBCName ):
		self.ODBCName = ODBCName
		self.db = odbc( self.ODBCName )
		self.cur = self.db.cursor()

	# convert any intrinsic Python types to the appropriate SQL type		
	def doPythonTypeConversions( self, val ):
		if type( val ) is long:
			return Long( val )
		if type( val ) is time.struct_time:
			return Time( val )
		else:
			return val
		
	# this method converts the list of column names into a tuple, and
	#  then removes the 's, converting the column names into a SQL list.
	def MakeSQLList( self, list ):
		list = map( self.doPythonTypeConversions, list )
		list = map( self.GetSQLRepr, list )
		return '(' + string.join( list, ', ' ) + ')'

	def MakeSQLFieldList( self, list ):
		return '(' + string.join( map( lambda x: '['+x+']', list ), ', ' ) + ')'

	def GetSQLRepr( self, object ):
		try:
			return object.SQLRepr
		except AttributeError:
			return repr( object )

	def Insert( self, table, values ):
		fields = self.MakeSQLFieldList( values.keys() )
		sql = 'INSERT INTO [%s] %s VALUES %s' % ( table, fields, self.MakeSQLList( values.values() ) )
		result = 0
		while not result:
			try:
				result = self.Execute( sql )
				if result != 1:
					raise DBException, 'Error with SQL: ' + sql
			except dbi.opError, message:
				if( message.find( 'currently locked by user' ) ):
					print 'Database locked, sleeping for 10 seconds'
					time.sleep(10)
					continue
				else:
					raise dbi.opError, message

	# Get the unique ID from the table of the form ( 'ID', 'Name' ) named
	#  '<Category> Types'.  If specified, create it if it doesn't exist (default).
	def GetTypeID( self, category, value, create = 1 ):
		params = {}
		params[ 'field' ] = 'Name'
		params[ 'table' ] = '%s Types' % category
		params[ 'id' ] = 'ID'
		params[ 'value' ] = value

		querySQL = "SELECT [%(id)s] from [%(table)s] where [%(field)s] = '%(value)s' " % params
		self.Execute( querySQL )
		result = self.cur.fetchone()
		if result:
			return result[0]
		if create:
			self.Insert( params[ 'table' ], { params[ 'field' ]: params[ 'value' ] } )
			return self.GetLastID()

	def GetLastID( self ):
		sql = "SELECT @@Identity"
		self.Execute( sql )
		result = self.cur.fetchone()
		if result:
			return result[0] # else return None

	def Exists( self, table, values ):
		self.Select( None, table, values )
		return self.cur.fetchone()

	def GetFieldIndex( self, field ):
		fieldNames = self.GetFieldNames()
		if type( field ) is types.IntType:
			result = field
		elif type( field ) is types.StringType:
			# note: should this be a case-insensitive search?
			result = fieldNames.index( field )
		else:
			raise TypeError, 'Field index must be a number or field name, not %s' % type( field )
		return result

	def GetDataAsDictionary( self, keyField = 0, valueField = 1 ):
		keyField = self.GetFieldIndex( keyField )
		valueField = self.GetFieldIndex( valueField )
		data = self.cur.fetchall()
		# transpose the data
		data = apply( zip, data )
		# get pairs of items to turn into a dictionary
		items = zip( data[ keyField ], data[ valueField ] )
		result = dict( items )
		return result

	def GetDataAsList( self, field = 0 ):
		field = self.GetFieldIndex( field )
		data = self.cur.fetchall()
		# transpose the data
		data = apply( zip, data )
		return data[ field ]
	
	def Select( self, fields, table, params = None, specifiers = None ):
		if not fields or fields == '*':
			fields = '*'
		elif type(fields) is types.StringType:
			fields = self.MakeSQLFieldList( [ fields ] )
		elif type(fields) is types.ListType:
			fields = self.MakeSQLFieldList( fields )
		sql = 'SELECT'
		if specifiers:
			sql = string.join( ( sql, ) + specifiers )
		sql = string.join( ( sql, fields, 'FROM', '[%s]' % table ) )
		if params:
			sql = string.join( ( sql, 'WHERE', self.BuildTests( params ) ) )
		self.Execute( sql )

	def Delete( self, table, params = None ):
		sql = 'DELETE * from [%s]' % table
		if params:
			sql = string.join( ( sql, 'WHERE', self.BuildTests( params ) ) )
		self.Execute( sql )

	def BuildTests( self, params ):
		tests = map( self.MakeSQLTest, params.items() )
		tests = string.join( tests, ' AND ' )
		return tests

	def MakeSQLTest( self, item ):
		field,value = item
		if value is None:
			fmt = '[%(field)s] is NULL'
		else:
			value = self.GetSQLRepr( value )
			fmt = '[%(field)s] = %(value)s'
		return fmt % vars()
	
	def GetFieldNames( self, table = None ):
		if table:
			sql = 'SELECT * from [%s] WHERE 0' % table
			self.Execute( sql )
		getFirstItem = lambda x: x[0]
		return map( getFirstItem, self.cur.description )

	def Execute( self, query ):
		self.lastQuery = query
		# execute the query.  If we get a program error, include the query with the message
		try:
			return self.cur.execute( query )
		except dbi.progError, message:
			raise dbi.progError, (message, self.lastQuery)
		except dbi.dataError, message:
			raise dbi.dataError, (message, self.lastQuery)
		except dbi.integrityError, message:
			raise dbi.integrityError, (message, self.lastQuery)

	def Update( self, table, criteria, updateParams ):
		updateParams = [ "[%s] = %s" % ( key, `value` ) for key, value in params.items() ]
		updateParams = string.join( updateParams, ', ' )
		criteria = self.BuildTests( criteria )
		sql = 'UPDATE %s SET %s WHERE %s' % (table, updateParams, criteria)
		self.Execute( sql )

	def AddObject( self, ob ):
		ob.AddToDB( self )

	def AddObjects( self, obs ):
		map( self.AddObject, obs )

	def GetAllRows( self ):
		return self.cur.fetchall()

# mix-in class for HTML generation in Database classes
class HTMLGenerator( object ):
	def GetAsHTMLTable( self, query = None ):
		if query:
			self.Execute( query )
		import win32com.client
		self.htmldoc = win32com.client.Dispatch( 'Msxml2.DOMDocument.4.0' )
		table = self.htmldoc.createElement( 'table' )
		table.setAttribute( 'class', 'dataDisplay' )
		self.tableElement = self.htmldoc.createElement( 'thead' )
		self.elementTag = 'th'
		self.AppendRow( self.GetFieldNames() )
		table.appendChild( self.tableElement )
		self.tableElement = self.htmldoc.createElement( 'tbody' )
		self.elementTag = 'td'
		map( self.AppendRow, self.GetAllRows() )
		table.appendChild( self.tableElement )

		result = table.xml
		del self.htmldoc, self.tableElement
		return result

	def AppendElement( self, value ):
		elem = self.htmldoc.createElement( self.elementTag )
		if value is not None:
			txt = self.htmldoc.createTextNode( value )
			elem.appendChild( txt )
		self.currentElement.appendChild( elem )

	def AppendRow( self, row ):
		self.currentElement = self.htmldoc.createElement( 'tr' )
		map( self.AppendElement, row )
		self.tableElement.appendChild( self.currentElement )
		