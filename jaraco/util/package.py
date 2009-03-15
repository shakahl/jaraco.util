#!/usr/bin/env python

import os

def read_long_description(setup_file):
	return open(
		os.path.join(
			os.path.dirname(setup_file),
			'docs',
			'index.txt',
		) ).read().strip()

