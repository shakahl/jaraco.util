# -*- coding: UTF-8 -*-

""" Setup script for building jaraco-util distribution

Copyright © 2004-2008 Jason R. Coombs
"""

from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

import os
import sys

# a quick little fix for PyPI
if sys.platform in ('win32',):
	if not os.environ.has_key('HOME'):
		drivepath = map(os.environ.get, ('HOMEDRIVE', 'HOMEPATH'))
		os.environ['HOME'] = os.path.join(*drivepath)

__author__ = 'Jason R. Coombs <jaraco@jaraco.com>'
__version__ = '$Rev$'[6:-2]
__svnauthor__ = '$Author$'[9:-2]
__date__ = '$Date$'[7:-2]

setup (name = 'jaraco.util',
		version = '1.5',
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
				'whois_bridge = jaraco.net.whois:main',
				'scanner = jaraco.net.scanner:scan',
				'fake-http = jaraco.net.http:start_simple_server',
				'wget = jaraco.net.http:wget',
				'fake-smtp = jaraco.net.smtp:start_simple_server',
				'udp-send = jaraco.net.udp:Sender',
				'udp-echo = jaraco.net.udp:EchoServer',
				'dns-forward-service = jaraco.net.dns:start_service',
				'roll-dice = jaraco.util.dice:do_dice_roll',
				'encode-dvd = jaraco.media.dvd:encode_dvd',
				'crop-detect = jaraco.media.cropdetect:execute',
				'dvd-info = jaraco.media.dvd_info:main',
				'dnsbl-check = jaraco.net.dnsbl:handle_cmdline',
				],
		},
		install_requires=[
			'clientform>=0.2.7',
			'BeautifulSoup',
		],
		extras_require = {
			'image':
				['pil>=1.1.6'],
#			'what_requires_this?': 
#				['pyxml>=0.8.4'],
		},
		dependency_links = [
			"http://www.jaraco.com/ASP/eggs",
		],
		tests_require=[
			'nose>=0.10',
		],
		test_suite = "nose.collector",
	)
