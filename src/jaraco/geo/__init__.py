# -*- coding: utf-8 -*-
#!python

import re
import operator
from jaraco.util.dictlib import DictMap

def split_sign(value):
	"""
	>>> split_sign(-5)
	(-1, 5)
	>>> split_sign(5)
	(1, 5)
	"""
	sign = [1, -1][value < 0]
	return sign, value*sign

def sign_string(sign):
	return ['', '-'][sign < 0]
	
class DMS(object):
	"""
	DMS - Degrees Minutes Seconds
	A class for parsing and manipulating polar coordinates in degrees,
	either as DMS or as decimal degrees (DD)
	
	>>> lat = DMS('-34.383333333')
	>>> float(lat) == -34.383333333
	True
	>>> value, sign = lat.DMS
	>>> value[0]
	34
	>>> value[1]
	23
	"""
	dmsPatterns = [
		# This pattern matches the DMS string that assumes little formatting.
		#  The numbers are bunched together, and it is assumed that the minutes
		#  and seconds are two digits each.
		"""
		(-)?			# optional negative sign
		(?P<deg>\d+)	# number of degrees (saved as 'deg')
		(?P<min>\d{2})	# number of minutes (saved as 'min')
		(?P<sec>\d{2})	# number of seconds (saved as 'sec')
		\s*				# optional whitespace
		([NSEW])?		# optional directional specifier
		$				# end of string
		""",
		# This pattern attempts to match all other possible specifications of
		#  DMS entry.
		"""
		(-)?			# optional negative sign
		(?P<deg>\d+		# number of degrees (saved as 'deg')
			(\.\d+)?	# optional fractional number of degrees (not saved separately)
		)				# all saved as 'deg'
		\s*				# optional whitespace
		(?:(°|deg))?	# optionally a degrees symbol or the word 'deg' (not saved)
		(?:				# begin optional minutes and seconds
			\s*?			# optional whitespace (matched minimally)
			[,]?			# optional comma or space (as a delimiter)
			\s*				# optional whitespace
			(?P<min>\d+)	# number of minutes (saved as 'min')
			\s*				# optional whitespace
			(?:('|min))?	# optionally a minutes symbol or the word 'min' (not saved)
			\s*?			# optional whitespace (matched minimally)
			[,]?			# optional comma or space (as a delimiter)
			(?:			# begin optional seconds
				\s*				# optional whitespace
				(?P<sec>\d+		# number of seconds
					(?:\.\d+)?	# optional fractional number of seconds (not saved separately)
				)				# (all saved as 'sec')
				\s*				# optional whitespace
				(?:("|sec))?	# optionally a minutes symbol or the word 'sec' (not saved)
			)?				# end optional seconds
		)?				# end optional minutes and seconds
		\s*				# optional whitespace
		([NSEW])?		# optional directional specifier
		$				# end of string
		"""
		]
	def __init__(self, DMSString = None):
		self.SetDMS(DMSString)

	def __float__(self):
		return self.dd

	def __unicode__(self):
		value, sign = self.DMS
		sign = sign_string(sign)
		return u'''%s%d° %d' %d"''' % ((sign,)+value)

	@staticmethod
	def get_dms_from_dd(dd, precision=2):
		sign, dd = split_sign(dd)
		int_round = lambda v: int(round(v, precision))
		deg = int_round(dd)
		fracMin = (dd - deg) * 60
		min = int_round(fracMin)
		sec = (fracMin - min) * 60
		return (deg, min, sec), sign

	def SetDMS(self, DMSString):
		self.DMSString = str(DMSString).strip()
		matches = filter(None, map(self._doPattern, self.dmsPatterns))
		if len(matches) == 0:
			raise ValueError, 'String %s did not match any DMS pattern' % self.DMSString
		bestMatch = matches[0]
		self.dd = self._getDDFromMatch(bestMatch)
		del self.DMSString

	def GetDMS(self):
		return self.get_dms_from_dd(self.dd)

	DMS = property(GetDMS, SetDMS)
	
	def _doPattern(self, pattern):
		expression = re.compile(pattern, re.IGNORECASE | re.VERBOSE)
		return expression.match(self.DMSString)
	
	def _getDDFromMatch(self, dmsMatch):
		# get the negative sign
		isNegative = operator.truth(dmsMatch.group(1))
		# get SW direction
		isSouthOrWest = operator.truth(dmsMatch.groups()[-1]) and dmsMatch.groups()[-1].lower() in ('s', 'w')
		d = dmsMatch.groupdict()
		# set min & sec to zero if they weren't matched
		if d['min'] is None: d['min'] = 0
		if d['sec'] is None: d['sec'] = 0
		# get the DMS and convert each to float
		d = DictMap(float, d)
		# convert the result to decimal format
		result = d['deg'] + d['min'] / 60 + d['sec'] / 3600
		if isNegative ^ isSouthOrWest: result = -result
		# validate the result
		if not (0 <= d['deg'] < 360 and 0 <= d['min'] < 60 and 0 <= d['sec'] < 60 and result >= -180):
			raise ValueError, 'DMS not given in valid range (%(deg)f°%(min)f\'%(sec)f").' % d
		return result
