# -*- coding: UTF-8 -*-

""" Setup script for building General Purpose Module distribution

Copyright © 2004-2008 Jason R. Coombs
"""

from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Rev$'[6:-2]
__svnauthor__ = '$Author$'[9:-2]
__date__ = '$Date$'[7:-2]

setup ( name = 'jaraco-util',
		version = '2.1',
		description = 'General utility modules to support functionality that Python maybe should support natively',
		author = 'Jason R. Coombs',
		author_email = 'jaraco@jaraco.com',
		url = 'http://www.jaraco.com/',
		packages = [''],
		package_dir = { '':'lib' },
		license = 'MIT',
		classifiers = [
			"Development Status :: 4 - Beta",
			"Intended Audience :: Developers",
			"Programming Language :: Python",
		],
		entry_points = {
			'console_scripts': [
				'whois_bridge = whois_bridge:main',
				],
		},
		install_requires=[
			'clientform>=0.2.7',
			'pyxml>=0.8.4',
		],
		dependency_links = [
			"http://www.jaraco.com/ASP/eggs",
		]
	)
