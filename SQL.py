# Module SQL defines SQL routines and classes for an ODBC link to
#  SQL databases.

import types, time, datetime
import string, re, sys, logging
import operator
import tools
import pywintypes # for TimeType
import encodings.ascii

log = logging.getLogger( 'SQL' )

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
			value = self.ConvertPyTimeToPythonTime( value )
		if type( value ) is datetime.datetime:
			value = value.utctimetuple()
		if type( value ) is datetime.date:
			value = value.timetuple()
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
		if type( other ) is Time:
			other = other.time
		return cmp( self.time, other )

	def ConvertPyTimeToPythonTime( self, pyt ):
		fmtString = '%Y-%m-%d %H:%M:%S'
		result = time.strptime( pyt.Format( fmtString ), fmtString )
		# make the time 'naive' by clearing the DST bit.
		return time.struct_time( result[:-1]+(0,) )

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

class String( unicode ):
	def _SQLRepr( self ):
		result = self.replace( "'", "''" )
		try:
			result = "'%s'" % str( result )
		except UnicodeEncodeError:
			result = u"N'%s'" % result
		return result
	SQLRepr = property( _SQLRepr )

def SQLQuote( name ):
	"take a SQL field name and quote it for use in a query"
	return '[%s]' % name

def MakeSQLQuotedList( list ):
	list = map( SQLQuote, list )
	return ', '.join( list )

def MakeSQLList( list ):
	list = map( GetSQLRepr, list )
	return '(' + string.join( list, ', ' ) + ')'

def MakeSQLFieldList( list ):
	return '(' + string.join( map( SQLQuote, list ), ', ' ) + ')'

def GetSQLRepr( object ):
	"Get an object's SQL representation"
	if hasattr( object, 'SQLRepr' ):
		result = object.SQLRepr
	else:
		# object doesn't have an explicit SQL representation.  Infer representation based
		#  on the python type.  If no inference is made, use the python representation.
		if type( object ) is types.LongType:
			# strip off the 'L' at the end
			result = object.__repr__( self )[:-1]
		elif isinstance( object, basestring ):
			# convert it to a SQL.String and get the repr
			result = String( object ).SQLRepr
		elif isinstance( object, ( time.struct_time, datetime.datetime, datetime.date, pywintypes.TimeType ) ):
			# convert it to a SQL.Time and get the repr
			result = Time( object ).SQLRepr
		elif object is None:
			result = 'NULL'
		elif isinstance( object, bool ):
			result = repr( int( object ) )
		else:
			result = repr( object )
	log.debug( 'SQL representation for %s is %s.' % ( object, result ) )
	log.debug( 'type( %s ) is %s.' % ( object, type( object ) ) )
	return result

import win32com.client
# Ensure that ADOs are available (either version 2.8 or 2.7)
try:
	# Microsoft ActiveX Data Objects 2.8 Library
	win32com.client.gencache.EnsureModule('{2A75196C-D9EB-4129-B803-931327F72D5C}', 0, 2, 8)
except pywintypes.com_error:
	# Microsoft ActiveX Data Objects 2.7 Library
	win32com.client.gencache.EnsureModule('{EF53050B-882E-4776-B643-EDA472E8E3F2}', 0, 2, 7)

class ADODatabase( object ):
	"""Class for performing ADO functionality.  See SQLServerDatabase
	for an example."""
	def __init__( self, parameters={} ):
		self.connectionParameters.update( parameters )
		self.connection = win32com.client.Dispatch( 'ADODB.Connection' )
		self.connect()

	def connect( self ):
		if self.connection.State:
			self.connection.Close()
		self.connection.Provider = self.provider
		self.__class__._setProperties( self.connection, self.connectionParameters )
		self.connection.Open()

	def _setProperties( object, properties ):
		for property, value in properties.items():
			object.Properties( property ).Value = value
	_setProperties = staticmethod( _setProperties )

	def MakeSQLList( self, list ):
		"""This method converts the list of column names into a tuple, and
then converts the list elements into their SQL representation."""
		list = map( GetSQLRepr, list )
		return '(' + string.join( list, ', ' ) + ')'

	def MakeSQLFieldList( self, list ):
		return '(' + string.join( map( SQLQuote, list ), ', ' ) + ')'

	def GetSQLRepr( self, object ):
		"Get an object's SQL representation -- deprecated, but kept for compatability."
		return GetSQLRepr( object )
	
	def Insert( self, table, values ):
		fields = self.MakeSQLFieldList( values.keys() )
		values = self.MakeSQLList( values.values() )
		table = SQLQuote( table )
		sql = 'INSERT INTO %(table)s %(fields)s VALUES %(values)s;' % vars()
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
		log.debug( 'Last ID was %s' % result )
		if result:
			result = int( result )
		return result

	def Exists( self, table, values ):
		self.Select( 'Count(*)', table, values )
		return operator.truth( self.GetSingletonResult() )

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
			data = zip( *data )
			# make into a dictionary
			data = dict( data )
			result = data
		else:
			result = {}
		return result

	def GetAllRows( self ):
		if not self.recordSet.EOF:
			data = self.recordSet.GetRows( -1, 0 )
			# transpose the data
			data = zip( *data )
			result = data
		else:
			result = ()
		return result

	def GetDataAsList( self, field = 0 ):
		if not self.recordSet.EOF:
			data = self.recordSet.GetRows( -1, 0, field )
			result = data[ 0 ]
		else:
			result = ()
		return result

	def GetResultAsObjects( self, ob = dict ):
		"Return a sequence of dictionaries with keys as field names and values from the rows."
		fieldNames = self.GetFieldNames()
		makeOb = lambda l: ob( zip( fieldNames, l ) )
		return map( makeOb, self.GetAllRows() )
	
	def BuildSelectQuery( self, fields, table, params = None, specifiers = None ):
		if not fields or fields == '*':
			fields = '*'
		elif isinstance( fields, basestring ):
			fields = MakeSQLQuotedList( [ fields ] )
		elif isinstance( fields, ( types.ListType, types.TupleType ) ):
			fields = MakeSQLQuotedList( fields )
		sql = 'SELECT'
		if specifiers:
			sql = string.join( ( sql, ) + specifiers )
		sql = string.join( ( sql, fields, 'FROM', SQLQuote( table ) ) )
		if params:
			sql = string.join( ( sql, 'WHERE', self.BuildTests( params ) ) )
		return sql

	def Select( self, *queryArgs ):
		__doc__ = self.BuildSelectQuery.__doc__
		sql = self.BuildSelectQuery( *queryArgs )
		self.Execute( sql )

	def Delete( self, table, params = None ):
		sql = 'DELETE from %s' % SQLQuote( table )
		if params:
			sql = string.join( ( sql, 'WHERE', self.BuildTests( params ) ) )
		self.Execute( sql )

	def BuildTests( self, params ):
		tests = map( self.MakeSQLTest, params.items() )
		tests = string.join( tests, ' AND ' )
		return tests

	def MakeSQLTest( self, item ):
		field,value = item
		field = SQLQuote( field )
		if value is None:
			fmt = '%(field)s is NULL'
		else:
			value = GetSQLRepr( value )
			fmt = '%(field)s = %(value)s'
		return fmt % vars()
	
	def GetFieldNames( self, table = None ):
		if table:
			table = SQLQuote( table )
			# run a query so as to retrieve the field names
			sql = 'SELECT * from %s WHERE 0=1' % table
			self.Execute( sql )
		getFieldName = lambda f: f.Name
		return map( getFieldName, self.recordSet.Fields )

	def Execute( self, query ):
		self.lastQuery = query
		log.debug( 'Executing query "%s".' % query )
		try:
			self.FlushRecordset()
			# execute the query.
			self.recordSet, result = self.connection.Execute( query )
		except:
			raise ExecuteException( sys.exc_value, self.lastQuery )
		log.debug( 'Query result is %d.' % result )
		# result is the number of records affected
		return result

	def Update( self, table, criteria, updateParams ):
		updateParams = tools.DictMap( GetSQLRepr, updateParams )
		updateParams = map( lambda p: '[%s] = %s' % p, updateParams.items() )
		updateParams = string.join( updateParams, ', ' )
		criteria = self.BuildTests( criteria )
		table = SQLQuote( table )
		sql = 'UPDATE %s SET %s WHERE %s' % (table, updateParams, criteria)
		self.Execute( sql )

	def GetSingletonResult( self ):
		if not self.recordSet.EOF:
			result = self.recordSet.Fields(0).Value
		else:
			log.info( 'Recordset is empty at call to GetSingletonResult.' )
			result = None
		return result

	def FlushRecordset( self ):
		# clear out any existing recordSet, or we run into a situation where we're
		#  in a sub-connection and things behave differently.
		if hasattr( self, 'recordSet' ):
			del self.recordSet
		
	def BeginTransaction( self, name = None ):
		self.FlushRecordset()
		res = self.connection.BeginTrans()
		msg = 'Beginning Transaction (%d transactions currently in progress).' % res
		log.debug( msg )
	
	def CommitTransaction( self, name = None ):
		self.FlushRecordset()
		self.connection.CommitTrans()
	
	def RollbackTransaction( self, name = None ):
		self.FlushRecordset()
		self.connection.CommitTrans()

	def ExecuteFile( self, filepath, encoding='utf-16' ):
		text = file( filepath, 'r' ).read().decode( encoding )
		# split the file into batches of code, segregated
		#  by 'GO' commands.  This is similar to how Query
		#  Analyzer executes a file.
		#  (?mi) means multi-line, case insensitive
		#  ^ means go should appear at the beginning of the line
		#  $ means nothing else should be on the line
		#  \s* means any amount of whitespace
		batches = re.split( '(?mi)^\s*GO\s*$', text )
		# filter out any empty strings or strings with only whitespace
		batches = filter( None, map( string.strip, batches ) )
		map( self.Execute, batches )

	def UseDatabase( self, dbName ):
		'Connect the current catalog in SQL server to dbName'
		try:
			log.debug( 'Attempting to change current catalog to %s.', dbName )
			self.connection.Properties('Current Catalog').Value = dbName
		except pywintypes.com_error, e:
			# sometimes, the name has to be in quotes for the initial call to set the current catalog.
			dbName = SQLQuote( dbName )
			log.debug( 'Attempting to change current catalog to %s.', dbName )
			self.connection.Properties('Current Catalog').Value = dbName

	def GetNextRowAsDictionary( self ):
		fieldNames = self.GetFieldNames()
		result = dict( zip( fieldNames, self.recordSet.Fields ) )
		return tools.DictMap( lambda d: d.Value, result )

	def MakeConnectionString( self, parameters ):
		makeSQLParameter = lambda p: string.join( p, '=' )
		parameters = map( makeSQLParameter, parameters.items() )
		parameters = string.join( parameters, '; ' )
		return parameters

	def GrantPermission( self, object, permission = 'SELECT', user = 'public' ):
		object = SQLQuote( object )
		query = 'GRANT %(permission)s ON %(object)s TO %(user)s'
		self.Execute( query )

	def GetUserTables( self ):
		self.Select( 'name', 'sysobjects', {'type':'U'} )
		return self.GetDataAsList()

	def ExecuteToStream( self, command ):
		result = win32com.client.Dispatch( 'ADODB.Stream' )
		result.Open()

		self.__class__._setProperties( command, { 'Output Stream': result } )
		try:
			adExecuteStream = win32com.client.constants.adExecuteStream
		except AttributeError, attribute:
			adExecuteStream = 1024
		command.Execute( None, Options = adExecuteStream )

		result.Position = 0
		return result

class AccessDatabase( ADODatabase ):
	connectionParameters = { }
	provider = 'Microsoft.Jet.OLEDB.4.0'

class ODBCDatabase( ADODatabase ):
	def __init__( self, ODBCName ):
		self.ODBCName = ODBCName
		self.connection = win32com.client.Dispatch( 'ADODB.Connection' )
		self.connection.Open( ODBCName )

	def SelectXML( self, *queryArgs ):
		sql = self.BuildSelectQuery( *queryArgs )
		sql = sql + ' For XML Auto'
		self.Execute( sql )

	def GetXMLResult( self ):
		if self.recordSet.EOF:
			result = ''
		else:
			result = string.replace( self.recordSet.GetString(), '\r', '' )
		return result

class SQLServerDatabase( ADODatabase ):
	provider = 'SQLOLEDB'
	connectionParameters = {}
	# use Windows integrated security by default
	connectionParameters['Integrated Security'] = 'SSPI'

	def Attach( self, dbName, files ):
		query = "exec sp_attach_db @dbname='%s'"
		filesString = string.join( files, ', ' )
		query = string.join( ( query, filesString ), ', ' )
		self.Execute( query )

	def SelectXML( self, *queryArgs ):
		__doc__ = ADODatabase.Select.__doc__
		sql = self.BuildSelectQuery( *queryArgs )
		sql = sql + ' For XML Auto'
		command = self.BuildCommand( sql )
		return self.ExecuteToStream( command )

	def BuildCommand( self, query ):
		command = win32com.client.Dispatch( 'ADODB.Command' )
		command.ActiveConnection = self.connection
		command.CommandText = query
		return command

	def RestoreDatabase( self, dbName, backupFilePath, moves = {} ):
		"moves is a dictionary of logical file name to physical file name mapping"
		query =  "restore database [%(dbname)s] from disk='%(backupFilePath)s'" % vars()
		if moves:
			moves = map( lambda m: "move '%s' to '%s'" % m, moves.items() )
			moves = ', '.join( moves )
			query = ' with '.join( ( query, moves ) )
		oldTimeout = self.connection.CommandTimeout
		self.connection.CommandTimeout = 999
		self.Execute( query )
		self.connection.CommandTimeout = oldTimeout

class SQLXMLDatabase( SQLServerDatabase ):
	provider = 'SQLXMLOLEDB'
	connectionParameters = {}
	connectionParameters.update( SQLServerDatabase.connectionParameters )
	connectionParameters['Data Provider'] = 'SQLOLEDB'

	def Execute( self, *args ):
		return self.ExecuteToStream( *args ).ReadText()

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
			value = self.MakeStringValue( value )
			txt = self.htmldoc.createTextNode( value )
			elem.appendChild( txt )
		self.currentElement.appendChild( elem )

	def AppendRow( self, row ):
		self.currentElement = self.htmldoc.createElement( 'tr' )
		map( self.AppendElement, row )
		self.tableElement.appendChild( self.currentElement )

	def MakeStringValue( self, value ):
		if type( value ) is pywintypes.TimeType:
			result = value.Format()
		else:
			result = str( value )
		return result
