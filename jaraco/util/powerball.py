import random
import sys

def quickPick( file = sys.stdout ):
	whiteBalls = range( 1, 54 )
	redBalls = range( 1, 43 )
	file.write( doDrawing( whiteBalls, redBalls ) + '\n' )

def doDrawing( whiteBalls, redBalls ):
	picked = map( lambda x: getBall( whiteBalls ), range( 5 ) )
	picked.sort()
	return '%s [%d]' % ( picked, getBall( redBalls ) )

def getBall( balls ):
	result = random.choice( balls )
	balls.remove( result )
	return result
