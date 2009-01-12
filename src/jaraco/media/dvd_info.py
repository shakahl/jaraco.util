#!/usr/bin/python
# -*- coding: utf-8 -*-

'''dvdinfo.py [--title n] [dvd device]
dvdinfo.py --help | -h

Displays information on the longest title on the DVD. If the dvd
device is not specified, /dev/dvd is used. You can also use a DVD
image as the device.

The title with the largest number of titles is considered the 'longest
title'. This is the feature film on the majority of the DVDs.

If you want to display the information on a specific title, pass the
title number with the --title option.
'''

# Changes:
#
# Version 1.1, 2006-08-13 13:00
#
#    - Only consider a title the main movie if it has an audio track.
#      This ensures that picture-titles with one chapter per picture
#      aren't considered the main movie, even though such titles can
#      have a lot of chapters.
#
#    - Added the ability to specify which title to read.
#
#    - Display 1/? instead of 1/1 if the total number of titles is
#      unknown.
#
# Version 1.0, released 2006-06-12 23:05
#
#    - Initial release

# COPYING: this software is released under the GPL licence. For more
# information, see http://www.stuvel.eu/licence

import re
from os import popen4
import sys
import getopt
import datetime

__author__ = '$Author$'[9:-2]
__email__ = 'jaraco@jaraco.com'
__revision__ = '2.0'
__url__ = 'http://www.jaraco.com'

device = 'd:'

def banner():
	'''Display the banner'''

	print 50*'='
	print 'dvdinfo.py version %s' % __revision__
	print '%s <%s>' % (__author__, __email__)
	print __url__
	print 50*'='
	print

class MetaTitleParser(type):
	"""
	A metaclass for title parsers that keeps track of all of them.
	"""
	
	_all_parsers = set()
	
	def __init__(cls, name, bases, attrs):
		cls._all_parsers.add(cls)
		# remove any base classes
		cls._all_parsers -= set(bases)

class TitleParser(object):
	__metaclass__ = MetaTitleParser
	
	def __init__(self, info):
		# info is the object that stores title info
		self.info = info
		self.pattern = re.compile(self.pattern)
	
	def __call__(self, line):
		self.parse(line)

	def parse(self, line):
		match = self.pattern.search(line)
		match and self.handle(match)
	
	@classmethod
	def create_all(cls, info):
		"Create all of the title parsers associated with this info"
		return [parser(info) for parser in cls._all_parsers]

class MaxTitlesParser(TitleParser):
	pattern = '^There are (?P<max_titles>\d+) titles'
	def handle(self, match):
		self.info['max_titles'] = int(match.groupdict()['max_titles'])

class ChaptersParser(TitleParser):
	pattern = '^There are (?P<chapters>\d+) chapters'
	def handle(self, match):
		self.info['chapters'] = int(match.groupdict()['chapters'])

class AudioParser(TitleParser):
	pattern = '^audio stream: (?P<stream>\d+) format: (?P<format>.+) language: (?P<language>.+) aid: (?P<aid>\d+)'
	def handle(self, match):
		'''Parse a single audio-channel line'''
		d = match.groupdict()
		d['aid'] = int(d['aid'])
		self.info['audiotracks'][d['aid']] = d

class SubtitleParser(TitleParser):
	pattern = '^subtitle \(\s*sid\s*\): (?P<sid>\d+) language: (?P<language>.*)'
	def handle(self, match):
		'''Parse a single subtitle-channel line'''
		d = match.groupdict()
		d['sid'] = int(d['sid'])
		self.info['subtitles'].append(d)

class NaviParser(TitleParser):
	pattern = 'Found NAVI packet!'
	def handle(self, match):
		self.info['navi_count']+=1

class LengthParser(TitleParser):
	pattern = 'ID_LENGTH=(?P<length>[\d.]+)'
	def handle(self, match):
		length = float(match.groupdict()['length'])
		length = datetime.timedelta(seconds=length)
		self.info['length'] = length

class TitleInfo(dict):
	def __init__(self, *args, **kwargs):
		self.update(max_titles=0, chapters=0, audiotracks={}, subtitles=[], navi_count=0)
		dict.__init__(self, *args, **kwargs)

def title_info(title):
	'''Returns title information about a single title.
	
	Returns a tuple max_titles, chapters, audiotracks, subtitles.
	'''

	# need at least two -v to get "Found NAVI packet"
	mpcmd = 'mplayer -v -v -v -identify -nosound -frames 0 -dvd-device %s dvd://%i -vo null'

	(mplayer_stdin, mplayer) = popen4(mpcmd % (device, title))
	
	mplayer_stdin.close()

	info = TitleInfo(number=title)

	parsers = TitleParser.create_all(info)

	for line in mplayer:
		for parser in parsers:
			parser(line)
		if info['navi_count'] > 100: break
	
	mplayer.close()
	#mplayer.wait()
	
	return info

def main():
	'''The main function'''

	global device

	# Set to the real value after the first read.
	max_title = '?'

	longest_title_info = None

	title = 1
	find_longest = True

	banner()

	# Parse options
	opts, args = getopt.gnu_getopt(sys.argv[1:], 'ht:', ('help',
		'title='))
	opts = dict(opts)

	if '-h' in opts or '--help' in opts:
		print __doc__
		return

	if '-t' in opts:
		title = int(opts['-t'])
		find_longest = False
	if '--title' in opts:
		title = int(opts['--title'])
		find_longest = False

	if args:
		device = args[0]

	if find_longest:
		# Walk through all titles
		while max_title == '?' or title <= max_title:
			sys.stdout.write('Reading title %i/%s   \r' % (title, max_title))
			sys.stdout.flush()

			info = title_info(title)

			# Remember info about the title with the most chapters,
			# but only if it has audio tracks.
			if info['audiotracks'] and (longest_title_info is None or info['chapters'] > longest_title_info['chapters']):
				longest_title_info = info

			title += 1
			max_title = info['max_titles']

		print 'Done reading.            '

		print 'Longest title: %s' % longest_title_info['number']
		info = longest_title_info
	else:
		print 'Reading title: %i' % title
		# Get info about given title
		info = title_info(title)
	
	if not max_title:
		raise SystemExit("Unable to find any titles on %s" % device)

	print 'Title length: %s' % info['length']

	print 'Chapters: %s' % info['chapters']

	print 'Audio tracks:'
	for aud_info in info['audiotracks'].itervalues():
		print '\taid=%(aid)3i lang=%(language)s fmt=%(format)s' % aud_info

	print 'Subtitles:'
	for st_info in info['subtitles']:
		print '\tsid=%(sid)3i lang=%(language)s' % st_info

if __name__ == '__main__':
	main()

