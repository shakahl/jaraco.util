import socket, sys, re, time
from optparse import OptionParser

p = OptionParser()
p.add_option('-p', '--port', type='int', help="Bind to port", default=80)
p.add_option('-t', '--timeout', type='int', help="Socket timeout", default=3)
p.add_option('-d', '--delay', type='float', help="Artificial delay in response", default=0)

options, args = p.parse_args()

def GetContentLength(request):
	match = re.search('^Content-Length:\s+(\d+)\s*$', request, re.I | re.MULTILINE)
	if match:
		return int(match.group(1))
	print >> sys.stderr, 'no content length found'

def GetHeaders(conn):
	res = ''
	while not '\r\n\r\n' in res:
		res += conn.recv(1024)
	bytes = len(res)
	res, content = res.split('\r\n\r\n')
	print >> sys.stderr, 'received %(bytes)d bytes' % vars()
	print res
	return res, content

def GetContent(conn, res, content):
	cl = GetContentLength(res) or 0
	while len(content) < cl:
		content += conn.recv(1024)
	bytes = len(content)
	print >> sys.stderr, 'received %(bytes)d bytes content' % vars()
	print content
	return content

def GetResponse(conn):
	try:
		conn.settimeout(options.timeout)
		res, content = GetHeaders(conn)
		content = GetContent(conn, res, content)
		conn.send('HTTP/1.0 200 OK\r\n')
		time.sleep(options.delay)
		conn.send('\r\nGot It!')
		conn.close()
	except socket.error, e:
		print 'Error %s' % e
		if res:
			print 'partial result'
			print repr(res)


def start_simple_server():
	"A simple web server that sends a simple response"
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.bind(('', options.port))
	s.listen(1)
	conn, addr = s.accept()
	print 'Accepted connection from', addr
	
	GetResponse(conn)
