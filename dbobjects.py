# -*- coding: UTF-8 -*-

""" dbobjects.py
Database objects

Must create a function in this module called getdb() which will return the SQL ADO Database
for retrieving the objects.
"""

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Revision: 3 $'[11:-2]
__vssauthor__ = '$Author: Jaraco $'[9:-2]
__date__ = '$Modtime: 4-10-04 13:57 $'[10:-2]

import xmlTools, tools, SQL

import re

import logging
log = logging.getLogger( __name__ )

class SimpleObject( xmlTools.XMLObject ):
	pkPattern = re.compile( "Violation of PRIMARY KEY constraint '.*'\. Cannot insert duplicate key in object '.*'\." )
	__autoInsert__ = True
	__autoRetrieve__ = True
	
	def __init__( self, *args ):
		self.__LoadFieldNames__()
		if not( len( args ) == 1 and isinstance( args[0], ( dict, tuple, list ) ) ):
			# parameters are not your usual dict initializers, so assume they correlate to
			#  the field names.
			args = ( zip( self.fieldNames, args ), )
		xmlTools.XMLObject.__init__( self, *args )

	def __repr__( self ):
		return '%s( %s )' % ( self.__class__.__name__, xmlTools.XMLObject.__repr__( self ) )

	def insert( self, data = None ):
		data = data or self
		try:
			getdb().Insert( self.tableName, data )
			id = getdb().GetLastID()
			if not id is None: self['ID'] = id
			log.log( 15, 'Inserted %s', self )
			return True
		except SQL.ExecuteException, e:
			self.__HandleException__( e )

	def __HandleException__( self, e ):
		ado_exc = e.orig[2]
		if ado_exc[5] == 0x80040e2f and self.pkPattern.match( ado_exc[2] ):
			log.debug( 'primary key conflict for %s', self )
		else:
			log.error( 'Failed adding %s to the database', self )
			log.error( e.orig[2][2] )
			raise

	def fetch( self ):
		results = self.GetAll( self )
		if len( results ) == 1:
			self.update( results[0] )
		elif len( results ) > 1:
			raise FetchError, 'More than one row returned for %s' % self
		return bool( len( results ) )

	def update_database( self ):
		"Update this object in the db. This method may need a better name; update is already taken."
		data = dict( self )
		self.__RemoveIdentityField__( data )
		getdb().Update( self.tableName, { self.IDField: self }, data )

	def __getitem__( self, key ):
		# trigger autofetch/insert of the object if the IDField is requested
		if key == self.IDField and not self.has_key( key ):
			self.fetch() or self.insert()
		return xmlTools.XMLObject.__getitem__( self, key )

	def __GetSQLRepr__( self ):
		"""Return the SQL Representation for this object."""
		try:
			return SQL.GetSQLRepr( self[ self.IDField ] )
		except KeyError:
			raise Exception, 'Could not acquire an object ID for object %s' % self
	SQLRepr = property( __GetSQLRepr__ )

	def GetAll( ob ):
		getdb().Select( '*', ob.tableName, ob )
		return getdb().GetResultAsObjects( ob.__class__ )
	GetAll = staticmethod( GetAll )

	def __LoadFieldNames__( self ):
		if not hasattr( self, 'fieldNames' ):
			self.__class__.fieldNames = getdb().GetFieldNames( self.tableName )
		if not hasattr( self, 'IDField' ):
			self.__class__.IDField = self.fieldNames[0]

	def __RemoveIdentityField__( self, data ):
		"Remove the identity column from the data if there is an identity column and it exists in the data"
		idcol = self.__GetIdentityColumn__()
		if idcol and idcol in data:
			del data[idcol]

	def __GetIdentityColumn__( self ):
		try:
			self.__identityColumn__
		except AttributeError:
			self.__class__.__identityColumn__ = getdb().GetIdentityColumn( self.tableName )
		return self.__identityColumn__

class SemistructuredObject( SimpleObject ):
	# __PrimaryFields__ (fieldNames) are the fields intrinsic to an object, the first of which
	# is assumed to be the identity of an object by default.
	# All other fields are supplementary fields.

	# want to ensure the database has the attribute table for this object
	def createAttributeTable( self ):
		raise NotImplementedError
		getdb().Execute( 'CREATE Table %s as ( Item %(valuefromparentobjectable)s, Name...' )
	
	def _SegregateData_( self ):
		"""Takes all data from the primary fields and separates it from the rest
of the data (supplementary)."""
		splitData = tools.hashSplit( self.items(), lambda ( key, value ): key in self.fieldNames )
		return map( dict, ( splitData[True], splitData[False] ) )

	def _SegregateFields_( self ):
		"""Finds the fields present in this object that are primary fields and those
that are supplementary, and returns a list for each."""
		splitFields = tools.hashSplit( self, lambda x: x in self.fieldNames )
		return splitFields[True], splitFields[False]
	
	def insert( self ):
		primaryData, supplementaryData = self._SegregateData_( )
		result = SimpleObject.insert( self, primaryData )
		map( self.__StoreAttribute__, supplementaryData.items() )

	def update_database( self ):
		primaryData, supplementaryData = self._SegregateData_( )
		self.__RemoveIdentityField__( primaryData )
		getdb().Update( self.tableName, { self.IDField: self }, primaryData )
		getdb().Delete( self.attributeTableName, { 'Item': self } )
		map( self.__StoreAttribute__, supplementaryData.items() )
		
	def __StoreAttribute__( self, item ):
		name,value = item
		getdb().Insert( self.attributeTableName, { 'Item': self, 'Name': name, 'Value': value } )

	def GetAll( ob ):
		# if ob is just a class, instanciate it to guarantee it has the fields we need
		if type( ob ) is type:
			ob = ob()
		primaryData, supplementaryData = ob._SegregateData_( )
		params = ob.tableName, ob.attributeTableName, ob.IDField
		baseQuery = """SELECT OB.*, ATTR.Name, ATTR.Value
		FROM [%s] OB left outer join [%s] ATTR on ATTR.[Item] = OB.[%s]""" % params
		joins, supTests = ob.__GetSupplementaryTests__( supplementaryData )
		tests = list( ob.__GetPrimaryTests__( primaryData ) )
		tests.extend( supTests )
		tests = ' and '.join( tests )
		query = ' '.join( ( baseQuery, ) + tuple( joins ) )
		if tests:
			query = ' '.join( ( query, 'WHERE', tests ) )
		getdb().Execute( query )
		return map( ob.__class__, getdb().GetPivotData() )
	GetAll = staticmethod( GetAll )

	def __GetSupplementaryTests__( self, supplementaryData ):
		joins = []
		tests = []
		for TestNumber, Item in enumerate( supplementaryData.items() ):
			IDField = self.IDField
			attributeTableName = self.attributeTableName
			tableName = self.tableName
			join = 'left outer join [%(attributeTableName)s] [Test%(TestNumber)d] on [Test%(TestNumber)d].[Item] = OB.[%(IDField)s]' % vars()
			Name, Value = map( SQL.GetSQLRepr, Item )
			test = '[Test%(TestNumber)d].[Name] = %(Name)s and [Test%(TestNumber)d].[Value] = %(Value)s' % vars()
			joins.append( join )
			tests.append( test )
		return joins, tests

	def __GetPrimaryTests__( self, primaryData ):
		for Name, Value in primaryData.items():
			Value = SQL.GetSQLRepr( Value )
			test = 'OB.[%(Name)s] = %(Value)s' % vars()
			yield test

	def __fetchAttributes__( self ):
		"Deprecated: use GetAll"
		getdb().Select( ( 'Name', 'Value' ), self.attributeTableName, { 'Item': self } )
		self.update( getdb().GetDataAsDictionary() )

	def MakeSupplementaryFields( objectClass, fields, removeNulls = True ):
		"""Take any data that's in the primary (static) field(s) of the table for this object
		and move it to the attributes table for this object"""
		if not hasattr( fields, '__iter__' ):
			fields = ( fields, )
		# cache the existing objects in memory
		objects = SemistructuredObject.GetAll( objectClass )
		for field in fields:
			del objectClass.fieldNames[ objectClass.fieldNames.index( field ) ]
		# refresh the database with the data
		map( lambda o: o.update_database( ), objects )
		# drop the static fields
		table = objectClass.tableName
		for field in fields:
			getdb().Execute( 'ALTER TABLE [%(table)s] DROP COLUMN [%(field)s]' % vars() )
		if removeNulls:
			getdb().Delete( objectClass.attributeTableName, { 'Name': fields, 'Value': None } )
	MakeSupplementaryFields = staticmethod( MakeSupplementaryFields )

# exceptions
class FetchError( Exception ): pass