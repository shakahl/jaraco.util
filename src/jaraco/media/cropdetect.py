import re
import win32api
import sys
from pywintypes import error
from itertools import imap, takewhile, ifilter


class consecutive_count(object):
	def __init__(self):
		self.count = 0
		self.last = None

	def __call__(self, item):
		if item == self.last:
			self.count += 1
		else:
			self.count = 0
			self.last = item
		return self.count

def consecutive_same(items):
	"""A generator that returns the count of consecutive
	preceeding items that match the current item.
	>>> tuple(consecutive_same([1,1,2,2,3,3,3]))
	(0,1,0,1,0,1,2)
	
	Note this will trivially produce zeros for most
	inputs.
	>>> tuple(consecutive_same([1,2,3]))
	(0,0,0)
	"""
	counter = consecutive_count()
	return imap(counter, items)

def within_consecutive_limit(limit):
	counter = consecutive_count()
	within_limit = lambda item: counter(item) < limit
	return within_limit

def get_args():
	from optparse import OptionParser
	parser = OptionParser()
	parser.add_option('-d', '--dvd-device', help="The drive or path to the files")
	parser.add_option('-t', '--title', help="The title to use", default="")
	options, args = parser.parse_args()
	
	if options.dvd_device: print "using device", options.dvd_device
	if options.title: print "using title", options.title

	args = [
		r"C:\Program Files (x86)\Slysoft\CloneDVDmobile\apps\mencoder.exe",
		"dvd://",
		"-nosound",
		"-vf", "cropdetect",
		"-ovc",	"lavc",
		"-o", "nul",
		"-chapter", "3-3",
		]

	args[1] = 'dvd://%(title)s' % options.__dict__

	if options.dvd_device:
		args[1:1] = [
			r"-dvd-device",
			options.dvd_device,
		]
	return args

def get_input():
	global mencoder
	from subprocess import Popen, PIPE, list2cmdline
	#print list2cmdline(mencoder_args)
	null = open('NUL', 'w')
	mencoder_args = get_args()
	mencoder = Popen(mencoder_args, stdout=PIPE, stderr=null)

def process_input():
	pattern = re.compile('.*crop=(\d+:\d+:\d+:\d+).*')
	
	crop_matches = ifilter(None, imap(pattern.match, mencoder.stdout))
	crop_values = imap(lambda match: match.group(1), crop_matches)
	n_frames = 1000
	preceeding_items = takewhile(within_consecutive_limit(n_frames), crop_values)

	print len(tuple(preceeding_items))
	try:
		target = crop_values.next()
		print target
	except StopIteration:
		print >> sys.stderr, "Not enough frames to detect %d consecutive same" % n_frames

def clean_up():
	try:
		win32api.TerminateProcess(int(mencoder._handle), -1)
		mencoder.stdout.flush()
	except error, e:
		pass # process is probably already terminated

if __name__ == '__main__':
	get_input()
	process_input()
	clean_up()