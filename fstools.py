# fstools.py:
#  tools for working with files and file systems
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
