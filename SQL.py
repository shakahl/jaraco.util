# -*- coding: UTF-8 -*-

"""SQL

	SQL Routines and classes for connecting to a SQL-based database.

	Currently, supports ADO databases (including ODBC), and native SQL
Server databases.
	
Copyright © 2004 Sandia National Laboratories  
"""

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Revision: 56 $a'[11:-2]
__vssauthor__ = '$Author: Jaraco $'[9:-2]
__date__ = '$Modtime: 9-12-04 13:16 $'[10:-2]

import types, time, datetime
import string, re, sys, logging, binascii
import operator, itertools
import tools
import pywintypes
import encodings.ascii

log = logging.getLogger( 'SQL' )

class ExecuteException( Exception ):
	def __init__( self, original_exc, query ):
		self.orig = original_exc
		self.query = query
		Exception.__init__( self )

	def __str__( self ):
		return '%s (%s)' % ( str( self.orig ), self.query )

DefaultTimeZone = None

import re, operator
class Binary( str ):
	def _SQLRepr( self ):
		return '0x' + self.ASCII

	SQLRepr = property( _SQLRepr )
	
	def _GetASCIIRepresentation( self ):
		return binascii.b2a_hex( self )

	ASCII = property( _GetASCIIRepresentation )

	def CreateFromASCIIRepresentation( s ):
		if re.match( '0x', s ):
			s = s[2:]
		return Binary( binascii.a2b_hex( s ) )

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
			# convert it to a datetime.datetime and get the repr
			dt = tools.ConstructDatetime( object )
			if DefaultTimeZone and dt.tzinfo:
				dt = dt.astimezone( DefaultTimeZone )
			result = tools.strftime( "{ Ts '%Y-%m-%d %H:%M:%S.%s' }", dt )
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

	def Quote( self, name ):
		"take a SQL field name and quote it for use in a query"
		return '[%s]' % name

	def BuildSQLQuotedList( self, list ):
		"Build a list of quoted objects (such as fields in a query)"
		list = map( self.Quote, list )
		return ', '.join( list )

	def BuildSQLList( self, list ):
		list = map( GetSQLRepr, list )
		return '(%s)' % ', '.join( list )

	def BuildSQLFieldList( self, list ):
		return '(%s)' % self.BuildSQLQuotedList( list )

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

	def GetSQLRepr( self, object ):
		"Get an object's SQL representation -- deprecated, but kept for compatability."
		return GetSQLRepr( object )
	
	def Insert( self, table, values ):
		fields = self.BuildSQLFieldList( values.keys() )
		values = self.BuildSQLList( values.values() )
		table = self.Quote( table )
		sql = 'INSERT INTO %(table)s %(fields)s VALUES %(values)s;' % vars()
		if not self.Execute( sql ) == 1:
			raise Exception, 'Error with SQL: ' + sql

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
	
	def BuildSelectQuery( self, fields, tables, params = None, specifiers = None ):
		if not fields or fields == '*':
			fields = '*'
		else:
			if not isinstance( fields, ( list, tuple ) ):
				fields = [ fields ]
			fields = self.BuildSQLQuotedList( fields )
		sql = 'SELECT'
		if specifiers:
			sql = string.join( ( sql, ) + specifiers )
		if not isinstance( tables, ( list, tuple ) ):
			tables = [ tables ]
		sql = string.join( ( sql, fields, 'FROM', self.BuildSQLQuotedList( tables ) ) )
		if params:
			sql = string.join( ( sql, 'WHERE', self.BuildTests( params ) ) )
		return sql

	def Select( self, *queryArgs ):
		__doc__ = self.BuildSelectQuery.__doc__
		sql = self.BuildSelectQuery( *queryArgs )
		return self.Execute( sql )

	def Delete( self, table, params = None ):
		sql = 'DELETE from %s' % self.Quote( table )
		if params:
			sql = string.join( ( sql, 'WHERE', self.BuildTests( params ) ) )
		self.Execute( sql )

	def BuildTests( self, params ):
		if isinstance( params, dict ):
			tests = map( self.MakeSQLTest, params.items() )
		elif isinstance( params, ( list, tuple ) ):
			tests = params
		tests = string.join( tests, ' AND ' )
		return tests

	def MakeSQLTest( self, item ):
		field,value = item
		field = self.Quote( field )
		if value is None:
			fmt = '%(field)s is NULL'
		elif isinstance( value, ( tuple, list ) ):
			fmt = '%(field)s in %(value)s'
			value = self.BuildSQLList( value )
		else:
			value = GetSQLRepr( value )
			fmt = '%(field)s = %(value)s'
		return fmt % vars()
	
	def GetFieldNames( self, table = None ):
		if table:
			table = self.Quote( table )
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
		table = self.Quote( table )
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
			dbName = self.Quote( dbName )
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
		object = self.Quote( object )
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

	def GetPivotData( self, PivotIndices = ( -2, -1 ) ):
		"""Retrieve the rowset and pivot on the last two columns as name/value pairs."""
		if not PivotIndices == ( -2, -1 ):
			raise NotImplementedError, 'Indices must be default in this implementation'
		fieldNames = self.GetFieldNames()
		map( fieldNames.__delitem__, PivotIndices )
		currentRow = None
		parameters = {}
		buildRowDict = lambda r, f, p: dict( zip( f, r ) + p.items() )
		for row in self.GetAllRows():
			row = list( row )
			newParam = map( row.__getitem__, PivotIndices )
			map( row.__delitem__, PivotIndices )
			if not currentRow == row:
				# new row detected
				if currentRow:
					yield buildRowDict( currentRow, fieldNames, parameters )
					parameters = {}
				currentRow = row
			if not None in newParam:
				parameters.__setitem__( *newParam )
		if currentRow:
			yield buildRowDict( currentRow, fieldNames, parameters )

	def GetAllRowsIter( self ):
		while not self.recordSet.EOF:
			result = self.recordSet.GetRows( 1 )
			# transpose the data
			result = zip( *result )[0]
			yield result

	def GetResultAsObjectsIter( self, ob = dict ):
		"Return a sequence of dictionaries with keys as field names and values from the rows."
		fieldNames = self.GetFieldNames()
		makeOb = lambda l: ob( zip( fieldNames, l ) )
		return itertools.imap( makeOb, self.GetAllRows() )

class AccessDatabase( ADODatabase ):
	connectionParameters = { }
	provider = 'Microsoft.Jet.OLEDB.4.0'

class ODBCDatabase( ADODatabase ):
	defaultParams = tools.odict()
	
	def __init__( self, spec_params ):
		params = tools.odict( self.defaultParams )
		if not isinstance( spec_params, dict ):
			spec_params = self.GetSingleParam( spec_params )
		params.update( spec_params )
		connectionString = self.BuildConnectionString( params )
		self.connection = win32com.client.Dispatch( 'ADODB.Connection' )
		log.debug( 'connect string is %s.', connectionString )
		self.connection.Open( connectionString )

	def GetSingleParam( self, param ):
		# assume spec_params is an ODBC data source name
		return tools.odict( { 'DSN': param } )
		
	def BuildConnectionString( self, params ):
		return ';'.join( map( '='.join, params.items() ) )

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

	def GetIdentityColumn( self, tableName ):
		query = "SELECT name from syscolumns where [id] = OBJECT_ID( '%(tableName)s' ) and ( [status] & 0x80 != 0 )" % vars()
		if self.Execute( query ):
			return self.GetSingletonResult()
			
class SQLXMLDatabase( SQLServerDatabase ):
	"A class for SQL-XML data.  Requires that SQLXML 3.0 be installed"
	provider = 'SQLXMLOLEDB'
	connectionParameters = {}
	connectionParameters.update( SQLServerDatabase.connectionParameters )
	connectionParameters['Data Provider'] = 'SQLOLEDB'

	def ExecuteToStream( self, command ):
		"Execute the command and return the textual XML result."
		return SQLServerDatabase.ExecuteToStream( self, command ).ReadText()

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
