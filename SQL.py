# Module SQL defines SQL routines and classes for an ODBC link to
#  SQL databases.

import types, time, string

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

	def __repr__( self ):
		return time.strftime( "{ Ts '%Y-%m-%d %H:%M:%S' }", self.time )
		return time.strftime( '#%Y/%m/%d %H:%M:%S#', self.time )

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
		even = range( 0, len( s ), 2 )
		odd = range( 1, len( s ), 2 )
		even = map( s.__getitem__, even )
		odd = map( s.__getitem__, odd )
		bytes = map( operator.add, even, odd )
		toBin = lambda byteStr: chr( long( byteStr, 16 ) )
		return Binary( string.join( map( toBin, bytes ), '' ) )

	CreateFromASCIIRepresentation = staticmethod( CreateFromASCIIRepresentation )	

class Long( long ):
	def __repr__( self ):
		# strip off the L at the end
		return long.__repr__( self )[:-1]

class Database( object ):
	def __init__( self, ODBCName ):
		self.ODBCName = ODBCName
		self.db = odbc( self.ODBCName )
		self.cur = self.db.cursor()
		
	def makeSQLLong( self, val ):
		if type( val ) is long:
			return Long( val )
		else:
			return val
		
	# this method converts the list of column names into a tuple, and
	#  then removes the 's, converting the column names into a SQL list.
	def MakeSQLList( self, list ):
		list = map( self.makeSQLLong, list )
		return '(' + string.join( map( self.GetSQLRepr, list ), ', ' ) + ')'

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

	def GetDataAsDictionary( self, keyField = 0, valueField = 1 ):
		getFirstItem = lambda x: x[0]
		fieldNames = map( getFirstItem, self.cur.description )
		if type( keyField ) is types.StringType:
			keyField = fieldNames.index( keyField )
		if type( valueField ) is types.StringType:
			valueField = fieldNames.index( valueField )
		data = self.cur.fetchall()
		result = {}
		for row in data:
			result[ row[ keyField ] ] = row[ valueField ]
		return result
	
	def Select( self, fields, table, params = None):
		if not fields or fields == '*':
			fields = '*'
		elif type(fields) is types.StringType:
			fields = self.MakeSQLFieldList( [ fields ] )
		elif type(fields) is types.ListType:
			fields = self.MakeSQLFieldList( fields )
		sql = 'SELECT %s from [%s]' % (fields, table)
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
		tests = string.join( tests, ' and ' )
		return tests

	def MakeSQLTest( self, item ):
		field,value = item
		if value is None:
			fmt = '[%(field)s] is NULL'
		else:
			value = `value`
			fmt = '[%(field)s] = %(value)s'
		return fmt % vars()
	
	def GetFieldNames( self, table = None ):
		if table:
			sql = 'SELECT * from [%s] WHERE 0' % table
			self.Execute( sql )
		return [ x[0] for x in self.cur.description ]

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