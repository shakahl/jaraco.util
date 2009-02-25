import os
import sys

def do_release():
	# a quick little fix for PyPI
	if sys.platform in ('win32',):
		if not os.environ.has_key('HOME'):
			drivepath = map(os.environ.get, ('HOMEDRIVE', 'HOMEPATH'))
			os.environ['HOME'] = os.path.join(*drivepath)

	sys.argv[1:] = ['egg_info', '-RDb', '', 'sdist', 'upload']
	execfile('setup.py')

if __name__ == '__main__':
	do_release()