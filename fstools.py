# -*- coding: UTF-8 -*-

"""fstools.py:
	tools for working with files and file systems
	
Copyright © 2004 Sandia National Laboratories  
"""

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Revision: 4 $'[11:-2]
__vssauthor__ = '$Author: Jaraco $'[9:-2]
__date__ = '$Modtime: 9-11-04 10:23 $'[10:-2]

import os, itertools

def GetUniquePathname( path, root = '' ):
	"""Return a pathname possibly with a number appended to it so that it is
	unique in the directory."""
	path = os.path.join( root, path )
	# consider the path supplied, then the paths with numbers appended
	potentialPaths = itertools.chain( ( path, ), __GetNumberedPaths__( path ) )
	potentialPaths = itertools.ifilterfalse( os.path.exists, potentialPaths )
	return potentialPaths.next()

GetUniqueFilename = GetUniquePathname

def __GetNumberedPaths__( filepath ):
	"""Append numbers in sequential order to the filename or folder name
	Numbers should be appended before the extension on a filename."""
	format = '%s (%%d)%s' % __splitext__( filepath )
	return itertools.imap( lambda n: format % n, itertools.count( 1 ) )

def __splitext__( filepath ):
	"Custom version of splitext that doesn't perform splitext on directories"
	if os.path.isdir( filepath ):
		return filepath, ''
	else:
		return os.path.splitext( filepath )