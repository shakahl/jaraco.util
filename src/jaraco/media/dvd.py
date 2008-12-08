#! python

import sys
import optparse
import re
import os
from os.path import join
from jaraco.util import flatten

rangePattern = re.compile('(\d+)(?:-(\d+))?')
delimiterPattern = re.compile('\s*[, ;]\s*')

def expandRange(title_range):
	start, stop = rangePattern.match(title_range)
	stop = stop or start
	return range(int(start), int(stop) + 1)

def getTitles(title_spec_string):
	title_specs = delimiterPattern.split(title_spec_string)
	title_specs = flatten(map(expandRange, title_specs))

def encode_dvd():
	parser = optparse.OptionParser()
	#parser.add_option('-t', '--titles', 'enter the title or titles to process (i.e. 1 or 1,5 or 1-5)' default='')
	parser.add_option('-t', '--title', help='enter the dvd title number to process', default='')
	options, args = parser.parse_args()

	mencoder = r'c:\Program Files (x86)\Slysoft\CloneDVDmobile\apps\mencoder.exe'

	# todo, print "device" list
	rips = join(os.environ['USERPROFILE'], 'videos', 'rips')

	assert len(args) <= 1
	if args:
		device = args[0]
	else:
		device = raw_input('enter device> ')
	assert os.path.exists(device), "Couldn't find device %s" % device

	print 'device is', device

	videos_path = join(os.environ['PUBLIC'], 'Videos', 'Movies')

	default_title = os.path.basename(device)
	title_prompt = 'Enter name of output [%s]> ' % default_title
	title = raw_input(title_prompt) or default_title

	filename = '%(title)s.mp4' % vars()
	target = os.path.join(videos_path, title)
	output_filename = os.path.join(videos_path, filename)

	dvd_title = options.title
	source = 'dvd://%(dvd_title)s' % vars()

	audio_options = '-oac copy -aid 128'.split()

	vid_filter = '-sws 2 -vf crop=720:464:0:8'.split()

	vid_opts='-ovc lavc -lavcopts vcodec=libx264:threads=2:vbitrate=1200:autoaspect'.split()

	gen_opts = ''
	if False: #todo: subtitle
		gen_opts = ' '.join(get_opts, '-sid 0')
	gen_opts = gen_opts.split()

	two_pass_temp_file = join(os.environ['USERPROFILE'], 'Videos', '%(title)s_pass.log' % vars())

	assert not os.path.exists(output_filename), 'Output file %(output_filename)s alread exists' % vars()

	first_pass_command = '"%(mencoder)s" %(source)s -dvd-device "%(device)s" %(vid_filter)s -nosound %(vid_opts)s:turbo:vpass=1 %(gen_opts)s -o nul -passlogfile "%(two_pass_temp_file)s"' % vars()
	second_pass_command = '"%(mencoder)s" %(source)s -dvd-device "%(device)s" %(vid_filter)s %(audio_options)s %(vid_opts)s:vpass=2 %(gen_opts)s -o "%(output_filename)s" -passlogfile "%(two_pass_temp_file)s"' % vars()

	args_template = [
		mencoder,
		source,
		'-dvd-device',
		device,
		vid_filter,
		audio_options,
		vid_opts,
		gen_opts,
		'-o',
		output_filename,
		]

	first_pass_args = list(args_template)
	first_pass_args[5] = '-nosound'
	first_pass_args[6] += ':turbo:vpass=1'
	first_pass_args[9] = 'nul'
	pass_log_file_args = ['-passlogfile', two_pass_temp_file]
	first_pass_args.extend(pass_log_file_args)

	second_pass_args = list(args_template)
	second_pass_args[6] += 'vpass=2'
	second_pass_args.extend(pass_log_file_args)

	first_pass_args=flatten(first_pass_args)
	second_pass_args=flatten(second_pass_args)

	import subprocess
	print 'executing with', first_pass_args
	proc = subprocess.Popen(first_pass_args)
	proc.wait()
	print 'executing with', second_pass_args
	proc = subprocess.Popen(second_pass_args)
	proc.wait()

	try:
		os.remove(two_pass_temp_file)
	except:
		pass # todo: log warning
