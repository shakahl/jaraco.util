#! python

import sys
import optparse
import re
import os
try:
	import win32api
except:
	pass
from os.path import join
from copy import deepcopy
from cStringIO import StringIO
from itertools import ifilter
import logging
from jaraco.util import flatten
from jaraco.media import cropdetect
from jaraco.util.odict import odict

log = logging.getLogger(__name__)

rangePattern = re.compile('(\d+)(?:-(\d+))?')
delimiterPattern = re.compile('\s*[, ;]\s*')

class DelimitedArgs(odict):
	value_join = '='
	
	def __str__(self):
		return self.delimiter.join(self.get_args())

	arg_items = odict.items

	def get_args(self):
		args = self.arg_items()
		remove_none_values = lambda item: filter(None, item)
		join_key_values = lambda item: self.value_join.join(item)
		args = map(join_key_values, map(remove_none_values, args))
		return args

class HyphenArgs(DelimitedArgs):
	"""
	Construct args suitable for unix-style command lines.
	
	e.g. -flag
	>>> print HyphenArgs({'flag':None})
	-flag
	
	e.g. -filename myfile.txt
	>>> print HyphenArgs(filename='myfile.txt')
	-filename myfile.txt
	
	>>> args = HyphenArgs([('a','a'), ('b','b')])
	>>> args_copy = args.copy()
	>>> print args_copy
	-a a -b b
	>>> print HyphenArgs([('a', '1'), ('b', None)])
	-a 1 -b
	""" 
	value_join=' '
	delimiter=' '
	
	@staticmethod
	def add_hyphen(value):
		return '-%s' % value

	def arg_items(self):
		return zip(self.hyphenated_keys(), self.values())

	def hyphenated_keys(self):
		return map(self.add_hyphen, super(self.__class__, self).keys())

	def __iter__(self):
		return ifilter(None, flatten(self.arg_items()))
		#for key, value in self.arg_items():
		#	yield key
		#	yield value

class ColonDelimitedArgs(DelimitedArgs):
	"""
	>>> print ColonDelimitedArgs(x='3', y='4')
	y=4:x=3
	"""
	delimiter = ':'
	
	def __iter__(self):
		yield str(self)

def guess_output_filename(name):
	"""
	>>> guess_output_filename('JEAN_DE_FLORETTE')
	'Jean De Florette'
	
	>>> guess_output_filename('')
	''
	"""
	names = name.split('_')
	names = map(str.capitalize, names)
	return ' '.join(names)

def infer_name(device):
	try:
		label = win32api.GetVolumeInformation(device)[0]
	except Exception:
		label = os.path.basename(device)
	return guess_output_filename(label)

class MEncoderCommand(object):
	"""
	>>> cmd = MEncoderCommand()
	>>> cmd.source = ['dvd://']
	>>> lavcopts = ColonDelimitedArgs(vcodec='libx264',threads='2',vbitrate='1200',autoaspect=None,)
	>>> cmd.video_options = HyphenArgs(lavcopts=lavcopts)
	>>> cmd2 = cmd.copy()
	>>> cmd_args = tuple(cmd.get_args())
	>>> cmd2_args = tuple(cmd2.get_args())
	>>> assert cmd_args == cmd2_args, '%s != %s' % (cmd_args, cmd2_args)
	"""
	
	exe_path = [r'c:\Program Files (x86)\Slysoft\CloneDVDmobile\apps\mencoder.exe']
	
	def __init__(self):
		self.other_options = HyphenArgs()

	def copy(self):
		result = MEncoderCommand()
		# we need to do a deep copy so we make copies of all the args
		result.__dict__.update(deepcopy(self.__dict__))
		return result

	def get_args(self):
		arg_order = 'exe_path', 'source', 'device', 'video_filter', 'video_options', 'audio_options', 'other_options'
		assert getattr(self, 'source', None) is not None
		for arg in arg_order:
			arg = getattr(self, arg, None)
			if arg is None: continue
			for value in arg:
				yield str(value)
	
	def set_device(self, value):
		assert os.path.exists(value), "Couldn't find device %s" % value
		self.device = HyphenArgs({'dvd-device': value})
		
	def __setitem__(self, key, value):
		self.other_options[key]=value

def expandRange(title_range):
	start, stop = rangePattern.match(title_range)
	stop = stop or start
	return range(int(start), int(stop) + 1)

def getTitles(title_spec_string):
	title_specs = delimiterPattern.split(title_spec_string)
	title_specs = flatten(map(expandRange, title_specs))

def generate_two_pass_commands(command):
	#two_pass_temp_file = join(os.environ['USERPROFILE'], 'Videos', '%(user_title)s_pass.log' % vars())
	filename, ext = os.path.splitext(command.other_options['o'])
	two_pass_temp_file = filename + '_pass.log'

	command = command.copy()
	command['passlogfile'] = two_pass_temp_file
	
	first_pass = command.copy()
	first_pass.audio_options=HyphenArgs(nosound=None)
	first_pass.video_options['lavcopts'].update(turbo=None, vpass='1')
	first_pass['o'] = 'nul' # TODO: /dev/null on linux

	second_pass = command.copy()
	second_pass.video_options['lavcopts'].update(vpass='2')
	return first_pass, second_pass

def encode_dvd():
	logging.basicConfig(level=logging.INFO)
	
	parser = optparse.OptionParser()
	#parser.add_option('-t', '--titles', 'enter the title or titles to process (i.e. 1 or 1,5 or 1-5)' default='')
	parser.add_option('-t', '--title', help='enter the dvd title number to process', default='')
	parser.add_option('-s', '--subtitle', help='enter the subtitle ID')
	options, args = parser.parse_args()

	command = MEncoderCommand()
	# todo, print "device" list
	rips = join(os.environ['USERPROFILE'], 'videos', 'rips')

	assert len(args) <= 1
	if args:
		device = args[0]
	else:
		device = raw_input('enter device> ')

	print 'device is', device
	command.set_device(device)

	videos_path = join(os.environ['PUBLIC'], 'Videos', 'Movies')

	default_title = infer_name(device)
	title_prompt = 'Enter output filename [%s]> ' % default_title
	user_title = raw_input(title_prompt) or default_title

	filename = '%(user_title)s.mp4' % vars()
	target = os.path.join(videos_path, user_title)
	output_filename = os.path.join(videos_path, filename)

	command['o'] = output_filename
	
	dvd_title = options.title
	command.source = ['dvd://%(dvd_title)s' % vars()]
	
	audio_options = HyphenArgs(
		oac='copy',
		aid='128',
		)
	command.audio_options = audio_options

	crop = cropdetect.get_crop(device, dvd_title)
	log.info('crop is %s', crop)
	command.video_filter = HyphenArgs(
		sws='2',
		vf=ColonDelimitedArgs(crop=crop),
		)

	# this is the setting I used for divx
	#set VID_OPTS=-ovc lavc -lavcopts vcodec=mpeg4:vhq:vbitrate=1200:autoaspect

	lavcopts = ColonDelimitedArgs(
		vcodec='libx264',
		threads='2',
		vbitrate='1200',
		autoaspect=None,
		)
	command.video_options=HyphenArgs(
		ovc='lavc',
		lavcopts=lavcopts,
		)

	if options.subtitle:
		command['sid'] = options.subtitle

	assert not os.path.exists(command.other_options['o']), 'Output file %s alread exists' % command.other_options['o']

	first_pass, second_pass = generate_two_pass_commands(command)

	first_pass_args = tuple(first_pass.get_args())
	second_pass_args = tuple(second_pass.get_args())

	errors = open('nul', 'w')

	#C:\Users\jaraco\Public>"C:\Program Files (x86)\Slysoft\CloneDVDmobile\apps\mencoder.exe" -dvd-device "C:\Users\jaraco\Videos\rips\JEAN_DE_FLORETTE" dvd:// -sws 2 -vf crop=720:352:0:62 -nosound -ovc lavc -lavcopts vcodec=libx264:threads=2:vbitrate=1200:autoaspect:turbo:vpass=1  -sid 0 -o nul -passlogfile"C:\Users\jaraco\Videos\Jean de Florette_pass.log"  2>nul

	import subprocess
	print 'executing with', first_pass_args
	proc = subprocess.Popen(first_pass_args, stderr=errors)
	proc.wait()
	print 'executing with', second_pass_args
	proc = subprocess.Popen(second_pass_args, stderr=errors)
	proc.wait()

	try:
		os.remove(two_pass_temp_file)
	except:
		pass # todo: log warning
