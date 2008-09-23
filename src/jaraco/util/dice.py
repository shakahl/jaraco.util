import random
import sys

def do_dice_roll():
	try:
		n_dice = int(sys.argv[1])
	except:
		n_dice = 1
	total = 0
	for dice in range(n_dice):
		value = random.randint(1,6)
		total += value
		print 'rolled %d' % value
	if n_dice > 1: print 'total %d' % total
