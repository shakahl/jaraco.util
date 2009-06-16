# -*- coding: UTF-8 -*-

""" Setup script for building jaraco-util distribution

Copyright © 2004-2009 Jason R. Coombs
"""

try:
	from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
	from distutils.command.build_py import build_py

from setuptools import setup, find_packages
try:
	from jaraco.util.package import read_long_description
	long_description = read_long_description()
except:
	long_description = None

__author__ = 'Jason R. Coombs <jaraco@jaraco.com>'
__version__ = '$Rev$'[6:-2]
__svnauthor__ = '$Author$'[9:-2]
__date__ = '$Date$'[7:-2]

name = 'jaraco.util'

setup (name = name,
		version = '3.0',
		description = 'General utility modules that supply commonly-used functionality',
		long_description = long_description,
		author = 'Jason R. Coombs',
		author_email = 'jaraco@jaraco.com',
		url = 'http://pypi.python.org/pypi/'+name,
		packages = find_packages(exclude=['ez_setup', 'tests', 'examples']),
		namespace_packages = ['jaraco',],
		license = 'MIT',
		classifiers = [
			"Development Status :: 4 - Beta",
			"Intended Audience :: Developers",
			"Programming Language :: Python",
		],
		entry_points = {
			'console_scripts': [
				'roll-dice = jaraco.util.dice:do_dice_roll',
				'release-package = jaraco.util.release:do_release',
				],
		},
		install_requires=[
		],
		extras_require = {
			'image':
				['pil>=1.1.6'],
		},
		dependency_links = [
		],
		tests_require=[
			'nose>=0.10',
		],
		test_suite = "nose.collector",
		cmdclass=dict(build_py=build_py),
	)
