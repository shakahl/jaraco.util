import os, sys, time
from threading import Thread
import traceback
from stat import *

# win32* requires ActivePython by Mark Hammond (thanks Mark!)
from win32file import *
from win32api import *
from win32event import *
from win32con import FILE_NOTIFY_CHANGE_LAST_WRITE


class ChangedSinceFilter( object ):
	def __init__( self, cutoff ):
		self.cutoff = cutoff

	def __call__( self, filepath ):
		last_mod = os.stat( filepath )[ST_MTIME]
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
					self.ProcessChangedFiles( )
					# reset the handle to the change notification and repeat
					FindNextChangeNotification( hChange )

				if result == WAIT_OBJECT_0 + 1:
					break

		except:
			# catch all exceptions and store the information so the calling
			#  thread can analyze the problem later.
			self.exception = ( sys.exc_info(), time.gmtime() )
			apply( traceback.print_exception, self.exception[0] )
		
		FindCloseChangeNotification( hChange )        

	def ProcessChangedFiles( self ):
		nextCheckTime = time.time()
		fileSpec = os.path.join( self.root, self.filter )
		# FindFiles returns tuples... The 9th element is the filename: extract it
		files = apply( zip, FindFiles( fileSpec ) )[8]
		# add the path to the filenames
		files = map( os.path.join, [ self.root ]*len( files ), files )
		# filter out the ones that haven't changed
		changed = filter( ChangedSinceFilter( self.lastCheckedTime ), files )
		# handle the ones that have
		map( self.Handle, changed )
		self.lastCheckedTime = nextCheckTime

class StatusHandler( object ):
	def __init__( self, output = sys.stdout ):
		self.output = output

	def __call__( self, filename ):
		self.output.write( '%s changed.\n' % filename )
		