import tools

quoteSubstitutions = ( ('"','&quot;'),
# leave out this substitution for now
#					   ("'",'&apos;')
					   )
reverseSubstitutions = tools.ReverseLists( quoteSubstitutions )

def ToXMLQuotedString( s ):
	return tools.ReplaceList( s, quoteSubstitutions )

def FromXMLQuotedString( s ):
	return tools.ReplaceList( s, reverseSubstitutions )

def GetXMLRepresentation( value ):
	"Get the appropriate XML representation for value"
	try:
		value = value.XMLRepr
	except AttributeError: pass
	# want to get the best precision for a float
	if isinstance( value, float ):
		value = repr( value )
	else:
		value = ToXMLQuotedString( value )
	return value

from datetime import datetime
from time import strptime
def ParseXMLTime( xmlTime ):
	"Take a time string in XML format and return the value as a datetime object"
	pattern = '%Y-%m-%dT%H:%M:%S'
	return datetime( *strptime( xmlTime, pattern )[:6] )