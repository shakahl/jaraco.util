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
class Time:
	def __init__( self, value ):
		if type( value ) is types.TupleType:
			self.time = value
		elif type( value ) is types.FloatType:
			self.time = time.gmtime( value )

	def __repr__( self ):
		return time.strftime( '#%Y/%m/%d %H:%M:%S#', self.time )

class Database:
	# this method converts the list of column names into a tuple, and
	#  then removes the 's, converting the column names into a SQL list.
	def MakeSQLList( self, list ):
		return '(' + string.join( map( repr, list ), ', ' ) + ')'

	def MakeSQLFieldList( self, list ):
		return '(' + string.join( map( lambda x: '['+x+']', list ), ', ' ) + ')'

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
		tests = [ "[%s] = %s" % ( key, `value` ) for key,value in params.items() ]
		tests = string.join( tests, ' and ' )
		return tests

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

	def Update( self, table, criteria, updateParams ):
		updateParams = [ "[%s] = %s" % ( key, `value` ) for key, value in params.items() ]
		updateParams = string.join( updateParams, ', ' )
		criteria = self.BuildTests( criteria )
		sql = 'UPDATE %s SET %s WHERE %s' % (table, updateParams, criteria)
		self.Execute( sql )
