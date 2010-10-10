# -*- coding: UTF-8 -*-

""" Setup script for building jaraco-util distribution

Copyright © 2004-2010 Jason R. Coombs
"""

try:
	from distutils.command.build_py import build_py_2to3 as build_py
	# exclude some fixers that break already compatible code
	from lib2to3.refactor import get_fixers_from_package
	fixers = get_fixers_from_package('lib2to3.fixes')
	for skip_fixer in ['import']:
		fixers.remove('lib2to3.fixes.fix_' + skip_fixer)
	build_py.fixer_names = fixers
except ImportError:
	from distutils.command.build_py import build_py

from setuptools import setup, find_packages

__author__ = 'Jason R. Coombs <jaraco@jaraco.com>'
__version__ = '$Rev$'[6:-2]
__svnauthor__ = '$Author$'[9:-2]
__date__ = '$Date$'[7:-2]

name = 'jaraco.util'

setup (name = name,
		use_hg_version_increment='0.1',
		description = 'General utility modules that supply commonly-used functionality',
		long_description = open('README').read(),
		author = 'Jason R. Coombs',
		author_email = 'jaraco@jaraco.com',
		url = 'http://pypi.python.org/pypi/'+name,
		packages = find_packages(exclude=['tests']),
		namespace_packages = ['jaraco',],
		license = 'MIT',
		classifiers = [
			"Development Status :: 4 - Beta",
			"Intended Audience :: Developers",
			"Programming Language :: Python",
			"Programming Language :: Python :: 3",
		],
		entry_points = {
			'console_scripts': [
				'roll-dice = jaraco.util.dice:do_dice_roll',
				'release-package = jaraco.util.package:release',
				'calc-prorate = jaraco.dateutil:calculate_prorated_values',
				'make-turk-recognition-job = jaraco.util.turk:make_turk_recognition_job_from_pdf',
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
		setup_requires=[
			'hgtools>=0.4',
		],
		cmdclass=dict(build_py=build_py),
	)
