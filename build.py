# -*- coding: UTF-8 -*-

""" Setup script for building General Purpose Module distribution

Copyright © 2004-2006 Jason R. Coombs
"""

from distutils.core import setup

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Rev$'[6:-2]
__svnauthor__ = '$Author$'[9:-2]
__date__ = '$Date$'[7:-2]

setup ( name = 'GeneralPurpose',
		version = '1.0.3',
		description = 'General Purpose Modules',
		author = 'Jason R. Coombs',
		author_email = 'jaraco@sandia.gov',
		packages = [''],
		package_dir = { '':'.' },
		script_args = ( 'bdist_wininst', )
		)
