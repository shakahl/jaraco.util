# -*- coding: UTF-8 -*-

""" Setup script for building General Purpose Module distribution

Copyright © 2004 Sandia National Laboratories
"""

from distutils.core import setup

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Revision: 1 $'[11:-2]
__vssauthor__ = '$Author: Jaraco $'[9:-2]
__date__ = '$Modtime: 15-12-04 15:39 $'[10:-2]

setup ( name = 'GeneralPurpose',
		version = '1.0',
		description = 'General Purpose Modules',
		author = 'Jason R. Coombs',
		author_email = 'jaraco@sandia.gov',
		packages = [''],
		package_dir = { '':'.' },
		script_args = ( 'bdist_wininst', )
		)
