# -*- coding: UTF-8 -*-

""" Setup script for building jaraco-util distribution

Copyright © 2004-2008 Jason R. Coombs
"""

from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

__author__ = 'Jason R. Coombs <jaraco@jaraco.com>'
__version__ = '$Rev$'[6:-2]
__svnauthor__ = '$Author$'[9:-2]
__date__ = '$Date$'[7:-2]

setup (name = 'jaraco.util',
		version = '1.1',
		description = 'General utility modules that supply commonly-used functionality',
		author = 'Jason R. Coombs',
		author_email = 'jaraco@jaraco.com',
		url = 'http://www.jaraco.com/',
		packages = find_packages('src'),
		package_dir = {'':'src'},
		namespace_packages = ['jaraco',],
		license = 'MIT',
		classifiers = [
			"Development Status :: 4 - Beta",
			"Intended Audience :: Developers",
			"Programming Language :: Python",
		],
		entry_points = {
			'console_scripts': [
				'whois_bridge = jaraco.net.whois:main',
				'scanner = jaraco.net.scanner:scan',
				'fake-http = jaraco.net.http:start_simple_server',
				'fake-smtp = jaraco.net.smtp:start_simple_server',
				],
		},
		install_requires=[
			'clientform>=0.2.7',
			'pyxml>=0.8.4',
		],
		dependency_links = [
			"http://www.jaraco.com/ASP/eggs",
		],
		tests_require=[
			'nose>=0.10',
		],
		test_suite = "nose.collector",
	)
