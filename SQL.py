# Module SQL defines SQL routines and classes for an ODBC link to
#  SQL databases.

import types, time, string, re, sys
import log
import pywintypes # for TimeType

class ExecuteException( Exception ):
	def __init__( self, original_exc, query ):
		self.orig = original_exc
		self.query = query
		Exception.__init__( self )

	def __str__( self ):
		return '%s (%s)' % ( str( self.orig ), self.query )

# Time is a time object used to correctly handle time with respect
#  to SQL queries.  Ideally, this should be replaced by the same
#  time object as is returned by a SQL query.
class Time( object ):
	def __init__( self, value ):
		# accomodate the time type returned by ADODB.Connection
		if type( value ) is pywintypes.TimeType:
			value = int( value )
		if type( value ) in ( types.TupleType, time.struct_time ):
			self.time = time.struct_time( value )
		elif type( value ) in ( types.FloatType, types.IntType, types.LongType ):
			self.time = time.gmtime( value )
		else:
			raise TypeError, 'Initialization value to Time must be a time tuple, GMT seconds, or ADODB.time'

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

import win32com.client # to get ADO objects
class Database( object ):
	def __init__( self, ODBCName ):
		self.ODBCName = ODBCName
		self.connection = win32com.client.Dispatch( 'ADODB.Connection' )
		self.connection.Open( ODBCName )

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
		values = self.MakeSQLList( values.values() )
		sql = 'INSERT INTO [%(table)s] %(fields)s VALUES %(values)s;' % vars()
		if not self.Execute( sql ) == 1:
			raise Exception, 'Error with SQL: ' + sql
		# delete the recordset to ensure the next recordset is from the same
		#  connection (especially important when checking for last identity)
		# (deprecated: moved to Execute method)
		#del self.recordSet

	def GetLastID( self ):
		sql = "SELECT @@IDENTITY;"
		self.Execute( sql )
		result = self.GetSingletonResult()
		log.processMessage( 'Last ID was %s' % result, 'SQL.Database', log.DEBUG )
		return result

	def Exists( self, table, values ):
		self.Select( 'Count(*)', table, values )
		return self.GetSingletonResult()

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
		if not self.recordSet.EOF:
			data = self.recordSet.GetRows( -1, 0, (keyField, valueField) )
			# transpose the data
			data = apply( zip, data )
			# make into a dictionary
			data = dict( data )
			result = data
		else:
			result = {}
		return result

	def GetDataAsList( self, field = 0 ):
		if not self.recordSet.EOF:
			data = self.recordSet.GetRows( -1, 0, field )
			result = data[ 0 ]
		else:
			result = ()
		return result
	
	def Select( self, *queryArgs ):
		sql = apply( self.BuildSelectQuery, queryArgs )
		self.Execute( sql )

	def SelectXML( self, *queryArgs ):
		sql = apply( self.BuildSelectQuery, queryArgs )
		sql = sql + ' For XML Auto'
		self.Execute( sql )

	def BuildSelectQuery( self, fields, table, params = None, specifiers = None ):
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
		return sql

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
			# run a query so as to retrieve the field names
			sql = 'SELECT * from [%s] WHERE 0=1' % table
			self.Execute( sql )
		getFieldName = lambda f: f.Name
		return map( getFieldName, self.recordSet.Fields )

	def Execute( self, query ):
		self.lastQuery = query
		log.processMessage( 'Executing query "%s".' % query, 'SQL.Database', log.DEBUG )
		try:
			# clear out any existing recordSet, or we run into a situation where we're
			#  in a sub-connection and things behave differently.
			if hasattr( self, 'recordSet' ): del self.recordSet
			# execute the query.
			self.recordSet, result = self.connection.Execute( query )
		except:
			raise ExecuteException( sys.exc_value, self.lastQuery )
		log.processMessage( 'Query result is %d.' % result, 'SQL.Database', log.DEBUG )
		# result is the number of records affected
		return result

	def Update( self, table, criteria, updateParams ):
		updateParams = map( lambda p: '[%s] = %s' % ( p[0], `p[1]` ), updateParams.items() )
		updateParams = string.join( updateParams, ', ' )
		criteria = self.BuildTests( criteria )
		sql = 'UPDATE %s SET %s WHERE %s' % (table, updateParams, criteria)
		self.Execute( sql )

	def GetSingletonResult( self ):
		if not self.recordSet.EOF:
			result = self.recordSet.Fields(0).Value
			self.recordSet.Close()
		else:
			log.processMessage( 'Recordset is empty at call to GetSingletonResult.', 'SQL.Database', log.WARNING )
			raise Exception, 'Recordset is empty at call to GetSingletonResult.'
		return result

	def GetXMLResult( self ):
		return string.replace( self.recordSet.GetString(), '\r', '' )

	def BeginTransaction( self, name = None ):
		query = 'BEGIN TRANSACTION'
		if name: query = string.join( ( query, name ) )
		self.Execute( query )
		del self.recordSet

	def CommitTransaction( self, name = None ):
		query = 'COMMIT TRANSACTION'
		if name: query = string.join( ( query, name ) )
		self.Execute( query )
		del self.recordSet

	def RollbackTransaction( self, name = None ):
		query = 'ROLLBACK TRANSACTION'
		if name: query = string.join( ( query, name ) )
		self.Execute( query )
		del self.recordSet

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
		