from __future__ import print_function

import random
import sys

def do_dice_roll():
	"""
	Roll n 6-sided dice and return each result and the total
	"""
	try:
		n_dice = int(sys.argv[1])
	except:
		n_dice = 1
	total = 0
	for dice in range(n_dice):
		value = random.randint(1,6)
		total += value
		print('rolled', value)
	if n_dice > 1: print('total', total)
