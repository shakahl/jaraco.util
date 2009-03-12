# -*- coding: UTF-8 -*-

""" Setup script for building jaraco-util distribution

Copyright © 2004-2009 Jason R. Coombs
"""

from setuptools import setup, find_packages

__author__ = 'Jason R. Coombs <jaraco@jaraco.com>'
__version__ = '$Rev$'[6:-2]
__svnauthor__ = '$Author$'[9:-2]
__date__ = '$Date$'[7:-2]

setup (name = 'jaraco.util',
		version = '2.2',
		description = 'General utility modules that supply commonly-used functionality',
		author = 'Jason R. Coombs',
		author_email = 'jaraco@jaraco.com',
		url = 'http://www.jaraco.com/',
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
	)
