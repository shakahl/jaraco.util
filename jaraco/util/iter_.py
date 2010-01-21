# -*- coding: UTF-8 -*-

"""jaraco.iter_
	Tools for working with iterables.  Complements itertools.
	
Copyright © 2008-2009 Jason R. Coombs
"""

__author__ = 'Jason R. Coombs <jaraco@jaraco.com>'
__version__ = '$Revision$'[11:-2]
__svnauthor__ = '$Author$'[9:-2]
__date__ = '$Date$'[7:-2]

import operator
import itertools
import sys
from jaraco.util import ordinalth
from jaraco.util.py26compat import basestring

class Count(object):
	"""
	A stop object that will count how many times it's been called and return
	False on the N+1st call.  Useful for use with takewhile.
	>>> tuple(itertools.takewhile(Count(5), range(20)))
	(0, 1, 2, 3, 4)
	"""
	def __init__(self, limit):
		self.count = 0
		self.limit = limit
		
	def __call__(self, arg):
		if not self.limit:
			result = True
		else:
			if self.count > self.limit:
				raise ValueError("Should not call count stop more anymore.")
			result = self.count < self.limit
		self.count += 1
		return result

	def __str__(self):
		if limit:
			return 'at most %d' % limit
		else:
			return 'all'

class islice(object):
	"""May be applied to an iterable to limit the number of items returned.
	Works similarly to count, except is called only once on an iterable.
	Functionality is identical to islice, except for __str__ and reusability.
	>>> tuple(islice(5).apply(range(20)))
	(0, 1, 2, 3, 4)
	>>> tuple(islice(None).apply(range(20)))
	(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19)
	"""
	def __init__(self, *sliceArgs):
		self.sliceArgs = sliceArgs

	def apply(self, i):
		return itertools.islice(i, *self.sliceArgs)

	def __str__(self):
		if self.sliceArgs == (None,):
			result = 'all'
		else:
			result = self._formatArgs()
		return result

	def _formatArgs(self):
		baseOneRange = lambda a_b: '%d to %d' % (a_b[0]+1,a_b[1])
		if len(self.sliceArgs) == 1:
			result = 'at most %d' % self.sliceArgs
		if len(self.sliceArgs) == 2:
			result = 'items %s' % baseOneRange(self.sliceArgs)
		if len(self.sliceArgs) == 3:
			result = 'every %s item from %s' % (ordinalth(self.sliceArgs[2]), baseOneRange(self.sliceArgs[0:2]))
		return result
	
class LessThanNBlanks(object):
	"""
	An object that when called will return True until n false elements
	are encountered.

	Can be used with filter or itertools.ifilter, for example:

>>> import itertools
>>> sampleData = ['string 1', 'string 2', '', 'string 3', '', 'string 4', '', '', 'string 5']
>>> first = itertools.takewhile(LessThanNBlanks(2), sampleData)
>>> tuple(first)
('string 1', 'string 2', '', 'string 3')
>>> first = itertools.takewhile(LessThanNBlanks(3), sampleData)
>>> tuple(first)
('string 1', 'string 2', '', 'string 3', '', 'string 4')
	"""
	def __init__(self, nBlanks):
		self.limit = nBlanks
		self.count = 0

	def __call__(self, arg):
		self.count += not arg
		if self.count > self.limit:
			raise ValueError("Should not call this object anymore.")
		return self.count < self.limit

class LessThanNConsecutiveBlanks(object):
	"""
	An object that when called will return True until n consecutive
	false elements are encountered.

	Can be used with filter or itertools.ifilter, for example:

>>> import itertools
>>> sampleData = ['string 1', 'string 2', '', 'string 3', '', 'string 4', '', '', 'string 5']
>>> first = itertools.takewhile(LessThanNConsecutiveBlanks(2), sampleData)
>>> tuple(first)
('string 1', 'string 2', '', 'string 3', '', 'string 4', '')
	"""
	
	def __init__(self, nBlanks):
		self.limit = nBlanks
		self.count = 0
		self.last = False
		
	def __call__(self, arg):
		self.count += not arg
		if arg:
			self.count = 0
		self.last = operator.truth(arg)
		if self.count > self.limit:
			raise ValueError("Should not call this object anymore.")
		return self.count < self.limit

class splitter(object):
	"""
	object that will split a string with the given arguments for each call
	>>> s = splitter(',')
	>>> list(s('hello, world, this is your, master calling'))
	['hello', ' world', ' this is your', ' master calling']
	"""
	def __init__(self, sep = None):
		self.sep = sep

	def __call__(self, s):
		lastIndex = 0
		while True:
			nextIndex = s.find(self.sep, lastIndex)
			if nextIndex != -1:
				yield s[lastIndex:nextIndex]
				lastIndex = nextIndex + 1
			else:
				yield s[lastIndex:]
				break

# From Python 3.1 docs
def grouper(n, iterable, fillvalue=None):
	"""
	grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx
	
	>>> c = grouper(3, range(11))
	>>> tuple(c)
	((0, 1, 2), (3, 4, 5), (6, 7, 8), (9, 10, None))
	"""
	args = [iter(iterable)] * n
	fn_name = ['izip_longest', 'zip_longest'][sys.version_info >= (3,0)]
	fn = getattr(itertools, fn_name)
	return fn(*args, fillvalue=fillvalue)

def grouper_nofill(n, iterable):
	"""
	Just like grouper, but doesn't add any fill values.

	>>> c = grouper_nofill(3, range(11))
	>>> tuple(c)
	((0, 1, 2), (3, 4, 5), (6, 7, 8), (9, 10))
	"""
	nofill = type('nofill', (object,), dict())
	value_is_not_nofill = lambda v: v is not nofill
	remove_nofill = lambda s: tuple(filter(value_is_not_nofill, s))
	result = grouper(n, iterable, fillvalue = nofill)
	return map(remove_nofill, result)
	

# from Python 2.6 docs
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)

def chain(sequences):
	"""functions like itertools.chain, except chains everything in sequences.
	Equivalent to itertools.chain(*sequences) except sequences is evaluated
	on demand."""
	for sequence in sequences:
		for item in sequence:
			yield item

def infiniteCall(f, *args):
	"Perpetually yield the result of calling function f."
	while True:
		yield f(*args)

def consume(i):
	"Cause an iterable to evaluate all of its arguments, but don't store any result."
	for x in i: pass

def consume_n(i, n):
	"Cause an iterable to evaluate n of its arguments, but don't store any result."
	consume(itertools.islice(i, n))

class Counter(object):
	def __init__(self, i):
		self.__count__ = 0
		self.__i__ = enumerate(i)

	def __iter__(self): return self

	def next(self):
		index, result = self.__i__.next()
		self.__count__ = index + 1
		return result

	def GetCount(self):
		return self.__count__

# todo, factor out caching capability
class iterable_test(dict):
	"Test objects for iterability, caching the result by type"
	def __init__(self, ignore_classes=[basestring]):
		"""ignore_classes must include str, because if a string
		is iterable, so is a single character, and the routine runs
		into an infinite recursion"""
		assert basestring in ignore_classes, 'str must be in ignore_classes'
		self.ignore_classes = ignore_classes

	def __getitem__(self, candidate):
		return dict.get(self, type(candidate)) or self._test(candidate)
			
	def _test(self, candidate):
		try:
			if isinstance(candidate, self.ignore_classes):
				raise TypeError
			iter(candidate)
			result = True
		except TypeError:
			result = False
		self[type(candidate)] = result
		return result

def iflatten(subject, test=None):
	if test is None:
		test = iterable_test()
	if not test[subject]:
		yield subject
	else:
		for elem in subject:
			for subelem in iflatten(elem, test):
				yield subelem

def flatten(subject, test=None):
	"""flatten an iterable with possible nested iterables.
	Adapted from
	http://mail.python.org/pipermail/python-list/2003-November/233971.html
	>>> flatten(['a','b',['c','d',['e','f'],'g'],'h']) == ['a','b','c','d','e','f','g','h']
	True

	Note this will normally ignore string types as iterables.
	>>> flatten(['ab', 'c'])
	['ab', 'c']
	"""
	return list(iflatten(subject, test))

def empty():
	"""
	An empty iterator.
	"""
	return iter(tuple())

class Reusable(object):
	"""
	An iterator that may be reset and reused.
	
	>>> ri = Reusable(range(3))
	>>> tuple(ri)
	(0, 1, 2)
	>>> next(ri)
	0
	>>> tuple(ri)
	(1, 2)
	>>> next(ri)
	0
	>>> ri.reset()
	>>> tuple(ri)
	(0, 1, 2)
	"""

	def __init__(self, iterable):
		self.__saved = iterable
		self.reset()

	def __iter__(self): return self

	def reset(self):
		"""
		Resets the iterator to the start.
		
		Any remaining values in the current iteration are discarded.
		"""
		self.__iterator, self.__saved = itertools.tee(self.__saved)

	def __next__(self):
		try:
			return next(self.__iterator)
		except StopIteration as e:
			# we're still going to raise the exception, but first
			#  reset the iterator so it's good for next time
			self.reset()
			raise

	if sys.version_info < (3,):
		next = __next__

# from Python 2.6 docs
def roundrobin(*iterables):
	"""
	>>> ' '.join(roundrobin('ABC', 'D', 'EF'))
	'A D E B F C'
	"""
	# Recipe credited to George Sakkis
	pending = len(iterables)
	next_attr = ['next', '__next__'][sys.version_info >= (3,)]
	nexts = itertools.cycle([getattr(iter(it), next_attr) for it in iterables])
	while pending:
		try:
			for next in nexts:
				yield next()
		except StopIteration:
			pending -= 1
			nexts = itertools.cycle(itertools.islice(nexts, pending))

# from Python 3.1 documentation
def unique_justseen(iterable, key=None):
	"""
	List unique elements, preserving order. Remember only the element just seen.

	>>> ' '.join(unique_justseen('AAAABBBCCDAABBB'))
	'A B C D A B'
	
	>>> ' '.join(unique_justseen('ABBCcAD', str.lower))
	'A B C A D'
	"""
	if sys.version_info < (3,0):
		map = itertools.imap
	return map(next, map(operator.itemgetter(1), itertools.groupby(iterable, key)))

