#!/usr/bin/env python

import os

def read_long_description():
	"""
	return the text in docs/index.txt
	"""
	return open(
		os.path.join(
			'docs',
			'index.txt',
		) ).read().strip()

