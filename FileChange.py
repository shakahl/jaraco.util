import os, sys, time, re, operator
from threading import Thread
import traceback
from stat import *
import itertools

import logging
log = logging.getLogger( 'FileChangeNotifier' )

# win32* requires ActivePython by Mark Hammond (thanks Mark!)
from win32file import *
from win32api import *
from win32event import *
from win32con import FILE_NOTIFY_CHANGE_LAST_WRITE


class ChangedSinceFilter( object ):
	def __init__( self, cutoff ):
		# truncate the time to the second.
		self.cutoff = int( cutoff )

	def __call__( self, filepath ):
		last_mod = os.stat( filepath )[ST_MTIME]
		log.debug( '%s last modified at %s.', filepath, time.asctime( time.localtime( last_mod ) ) )
		return last_mod >= self.cutoff

class FileChangeNotifierException( Exception ):
	pass

# FileChangeNotifier provides a simple interface that calls the handler
#  for each file that is updated matching root\filter
# Note: files are only checked in the root directory (subdirectories ignored)
# Note: files that are updated while the handler is processing are not caught

class FileChangeNotifier( Thread ):
	def __init__( self, root = '.', filter = '*', handler = lambda file: None ):
		# init thread stuff
		Thread.__init__( self )
		# set it as a daemon thread so that it doesn't block waiting to close.
		#  I tried setting __del__( self ) to .Quit(), but unfortunately, there are
		#  references to this object in the win32api stuff, so __del__ never gets
		#  called.
		self.setDaemon( 1 )
		
		# assign the root, verify it exists
		self.root = root
		if not os.path.isdir( self.root ):
			raise FileChangeNotifierException( 'Root directory %s does not exist' % self.root )

		# assign the filter and handler
		self.filter = filter
		self.Handle = handler

		self.QuitEvent = CreateEvent( None, 0, 0, None )

		self.watchSubtree = 0		

	def Quit( self ):
		SetEvent( self.QuitEvent )

	def run( self ):
		# set up to monitor the directory tree specified
		hChange = FindFirstChangeNotification( self.root, 0, \
											   FILE_NOTIFY_CHANGE_LAST_WRITE )

		# make sure it worked; if not, bail
		if hChange == INVALID_HANDLE_VALUE:
			raise FileChangeNotifierException, 'Could not set up directory change notification'

		# continuously monitor files and handle them if they've changed
		try:
			# make account of when we started waiting for updates
			self.lastCheckedTime = time.time()
			while (1):
				# block (sleep) until something changes in the
				#  target directory or a quit is requested.
				# timeout so we can catch keyboard interrupts or other exceptions
				result = WAIT_TIMEOUT
				while result == WAIT_TIMEOUT:
					result = WaitForMultipleObjects( ( hChange, self.QuitEvent ), 0, 1000 )

				if result == WAIT_OBJECT_0 + 0:
					# something has changed.  Check all of the files
					# that match the filter.
					nextCheckTime = time.time()
					log.debug( 'Looking for all files changed after %s', time.asctime( time.localtime( self.lastCheckedTime ) )  )
					self.ProcessChangedFiles( )
					self.lastCheckedTime = nextCheckTime
					# reset the handle to the change notification and repeat
					FindNextChangeNotification( hChange )

				if result == WAIT_OBJECT_0 + 1:
					break

		except:
			# catch all exceptions and store the information so the calling
			#  thread can analyze the problem later.
			self.exception = ( sys.exc_info(), time.gmtime() )
			traceback.print_exc()
		
		FindCloseChangeNotification( hChange )        

	def ProcessChangedFiles( self, path = None ):
		if not path:
			path = self.root
		fileSpec = os.path.join( path, self.filter )
		log.debug( 'Looking for changed files matching %s', fileSpec )
		files = FindFiles( fileSpec )
		if files:
			# FindFiles returns tuples... The 9th element is the filename: extract it
			files = zip( *files )[8]
		# create a function for prepending the path
		prepender = lambda x: os.path.join( path, x )
		# add the path to the filenames
		files = map( prepender, files )
		# filter out the ones that haven't changed
		changed = filter( ChangedSinceFilter( self.lastCheckedTime ), files )
		log.debug( 'These files have changed: %s', changed )
		# handle the ones that have
		map( self.Handle, changed )
		if self.watchSubtree:
			directories = map( prepender, os.listdir( path ) )
			directories = filter( os.path.isdir, directories )
			map( self.ProcessChangedFiles, directories )

	def WatchSubtree( self, choice = 1 ):
		self.watchSubtree = choice

# the status handler is a sample handler object that will
#  announce that a file has changed.
class StatusHandler( object ):
	def __init__( self, output = sys.stdout ):
		self.output = output

	def __call__( self, filename ):
		self.output.write( '%s changed.\n' % filename )

class FileFilter( object ):
	pass

class ModifiedTimeFilter( FileFilter ):
	""" Returns true for each call where the modified time of the file is after the cutoff time """
	def __init__( self, cutoff ):
		# truncate the time to the second.
		self.cutoff = int( cutoff )

	def __call__( self, filepath ):
		last_mod = os.stat( filepath ).st_mtime
		log.debug( '%s last modified at %s.', filepath, time.asctime( time.localtime( last_mod ) ) )
		return last_mod >= self.cutoff

class PatternFilter( FileFilter ):
	def __init__( self, filePattern = None, rePattern = None ):
		if filePattern and rePattern:
			raise TypeError, 'PatternFilter() takes exactly 1 argument (2 given).'
		if not filePattern and not rePattern:
			raise TypeError, 'PatternFilter() takes exactly 1 argument (0 given).'
		if filePattern:
			self.pattern = self.ConvertFilePattern( filePattern )
		if rePattern:
			self.pattern = rePattern

	def ConvertFilePattern( p ):
		"""
		converts a filename specification (such as c:\*.*) to an equivelent regular expression
		>>> PatternFilter.ConvertFilePattern( 'c:\\*' )
		'c:\\\\.*'
		"""
		import string
		subs = ( ( '\\', '\\\\' ), ( '.', '\\.' ), ( '*', '.*' ), ( '?', '.' ) )
		for old, new in subs:
			p = string.replace( p, old, new )
		return p
	ConvertFilePattern = staticmethod( ConvertFilePattern )

	def __call__( self, filepath ):
		filename = os.path.basename( filepath )
		return operator.truth( re.match( self.pattern, filename ) )

class AggregateFilter( FileFilter ):
	def __init__( self, *filters ):
		self.filters = filters

	def __call__( self, filepath ):
		results = map( lambda x: x( filepath ), self.filters )
		result = reduce( operator.and_, results )
		return result

def filesWithPath( files, path ):
	for file in files:
		yield os.path.join( path, file )

def GetFilePaths( walkResult ):
	root, dirs, files = walkResult
	return filesWithPath( files, root )

class Notifier( object ):
	def __init__( self, root = '.', filters = [] ):
		# assign the root, verify it exists
		self.root = root
		if not os.path.isdir( self.root ):
			raise FileChangeNotifierException( 'Root directory "%s" does not exist' % self.root )
		self.filters = filters

		self.watchSubtree = False
		self.QuitEvent = CreateEvent( None, 0, 0, None )

	def __del__( self ):
		try:
			FindCloseChangeNotification( self.hChange )
		except: pass

	def _GetChangeHandle( self ):
		# set up to monitor the directory tree specified
		self.hChange = FindFirstChangeNotification( self.root, 0, \
											   FILE_NOTIFY_CHANGE_LAST_WRITE )

		# make sure it worked; if not, bail
		if self.hChange == INVALID_HANDLE_VALUE:
			raise FileChangeNotifierException, 'Could not set up directory change notification'

	def _FilteredWalk( path, fileFilter ):
		"""static method that calls os.walk, but filters out anything that doesn't match the filter"""
		for root, dirs, files in os.walk( path ):
			log.debug( 'looking in %s', root )
			log.debug( 'files is %s', files )
			files = filter( fileFilter, filesWithPath( files, root ) )
			log.debug( 'filtered files is %s', files )
			yield ( root, dirs, files )
	_FilteredWalk = staticmethod( _FilteredWalk )

	def Quit( self ):
		SetEvent( self.QuitEvent )

class ThreadedNotifier( Notifier ):
	"""This class will replace FileChangeNotifier above"""
	pass

def WaitResults( *args ):
	""" calls WaitForMultipleObjects repeatedly with args """
	return itertools.starmap( WaitForMultipleObjects, itertools.repeat( args ) )

class BlockingNotifier( Notifier ):

	def GetChangedFiles( self ):
		self._GetChangeHandle()
		checkTime = time.time()
		# block (sleep) until something changes in the
		#  target directory or a quit is requested.
		# timeout so we can catch keyboard interrupts or other exceptions
		for result in WaitResults( ( self.hChange, self.QuitEvent ), False, 1000 ):
			if result == WAIT_OBJECT_0 + 0:
				# something has changed.
				log.debug( 'Change notification received' )
				nextCheckTime = time.time()
				FindNextChangeNotification( self.hChange )
				log.debug( 'Looking for all files changed after %s', time.asctime( time.localtime( checkTime ) ) )
				for file in self.FindFilesAfter( checkTime ):
					yield file
				checkTime = nextCheckTime
			if result == WAIT_OBJECT_0 + 1:
				# quit was received, stop yielding stuff
				return
			else:
				pass # it was a timeout.  ignore it and wait some more.
		
	def FindFilesAfter( self, cutoff ):
		mtf = ModifiedTimeFilter( cutoff )
		af = AggregateFilter( mtf, *self.filters )
		results = Notifier._FilteredWalk( self.root, af )
		results = itertools.imap( GetFilePaths, results )
		if self.watchSubtree:
			result = itertools.chain( *results )
		else:
			result = results.next()
		return result

