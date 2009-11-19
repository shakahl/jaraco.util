"""
Python 3 backward compatibility hooks for Python 2.6, 2.7
"""

try:
	int = long
except NameError:
	int = int

try:
	str = unicode
except NameError:
	str = str

try:
	import thread as threading
except ImportError:
	import threading

try:
	basestring = basestring
except NameError:
	basestring = str
