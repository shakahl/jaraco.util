#!/usr/bin/env python

# modified 2001-10-19

import os, sys
from threading import Thread
import time
import traceback
from stat import *

# win32* requires ActivePython by Mark Hammond (thanks Mark!)
from win32file import *
from win32api import *
from win32event import *
from win32con import FILE_NOTIFY_CHANGE_LAST_WRITE

class FileChangeNotifierException:
    def __init__( self, value='unspecified error' ):
        self.value = value

    def __str__( self ):
        return self.value


# FileChangeNotifier provides a simple interface that calls the handler
#  for each file that is updated matching root\filter
# Note: files are only checked in the root directory (subdirectories ignored)
# Note: files that are updated while the handler is processing are not caught

class FileChangeNotifier( Thread ):
    def __init__( self, root = os.sep, filter = '*', handler = lambda: None ):
        # init thread stuff
        Thread.__init__( self )
        
        # assign the root, verify it exists, and make sure it ends
        #  in a backslash (\)
        self.root = root
        if not os.path.isdir( self.root ):
            raise FileChangeNotifierException( 'Root directory %s does not exist' % self.root )
        if not self.root[-1] == os.sep:
            self.root += os.sep

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
            print 'Error getting Change Notification Handle'
            raise FileChangeNotifierException( 'Could not set up directory change notification' )

        # continuously monitor files and handle them if they've changed
        try:
            while (1):
                # make account of when we started waiting for updates
                lastCheckedTime = time.time()
                # block (sleep) until something changes in the
                #  target directory or a quit is requested.
                # timeout so we can catch keyboard interrupts or other exceptions
                result = WAIT_TIMEOUT
                while result == WAIT_TIMEOUT:
                    result = WaitForMultipleObjects( ( hChange, self.QuitEvent ), 0, 1000 )

                if result == WAIT_OBJECT_0 + 1:
                    break

                # something has changed.  Check all of the files
                # that match the filter.
                for file in FindFiles( self.root + self.filter ):
                    # append the directory to the filename
                    filepath = self.root + file[8]
                    last_mod = os.stat( filepath )[ST_MTIME]
                    # I could have used the following command, but
                    # it was returning local time, not UTC, so use os.stat
                    #last_mod = int( file[3] )
                    if last_mod >= lastCheckedTime:
                        self.Handle( filepath )
                    # reset the handle to the change notification and repeat
                    FindNextChangeNotification( hChange )
        except:
            # catch all exceptions and store the information so the calling
            #  thread can analyze the problem later.
            self.exception = ( sys.exc_info(), time.gmtime() )
            apply( traceback.print_exception, self.exception[0] )
        
        FindCloseChangeNotification( hChange )        
