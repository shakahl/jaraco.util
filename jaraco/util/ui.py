from __future__ import print_function
from itertools import count

class Menu(object):
	"""
	A simple command-line based menu
	"""
	def __init__(self, choices=None):
		self.choices = choices or list()

	def get_choice(self, prompt="> "):
		number_width = len(self.choices)/10+1
		menu_fmt = '{number:{number_width}}) {choice}'
		for number, choice in zip(count(1), self.choices):
			print(menu_fmt.format(**vars()))
		print()
		try:
			answer = int(raw_input(prompt))
			result = self.choices[answer-1]
		except ValueError:
			print('invalid selection')
			result = None
		except IndexError:
			print('invalid selection')
			result = None
		except KeyboardInterrupt:
			result = None
		return result

