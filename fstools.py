# -*- coding: UTF-8 -*-

"""fstools.py:
	tools for working with files and file systems
	
Copyright © 2004 Sandia National Laboratories  
"""

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Revision: 3 $'[11:-2]
__vssauthor__ = '$Author: Jaraco $'[9:-2]
__date__ = '$Modtime: 04-06-23 12:22 $'[10:-2]

import os

# return a filename possibly with a number appended to it so that it is
#  unique in the directory
def GetUniqueFilename( filename, directory ):
	basename, ext = os.path.splitext( filename )
	# save the file with the original name.  If it already exists,
	#  append a number to the end so as not to overwrite the original
	number = 0
	newFilename = filename
	while 1:
		destination = os.path.join( directory, newFilename )
		if not os.path.exists( destination ): break
		number += 1
		newFilename = '%s (%d)%s' % ( basename, number, ext )

	return newFilename
