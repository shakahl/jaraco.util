from util.string import multi_substitution

def ConvertFilePattern(p):
	r"""
	converts a filename specification (such as c:\*.*) to an equivelent regular expression
	>>> ConvertFilePattern('c:\*')
	'c:\\\\.*'
	"""
	return multi_substitution()(p)
