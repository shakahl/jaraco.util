import string


import smtplib, socket
class SMTPMailbox:
	def __init__( self, address ):
		self.Address = address

	def Notify( self, msg = '', importance = 'Normal' ):        
		import smtplib
		fromaddr = 'SMTP Notifier <notifier@%s>' % socket.getfqdn()
		toaddr = self.Address
		Headers = { 'From': fromaddr, 'To': toaddr, 'Importance':importance, 'Subject':'Notification' }

		server = smtplib.SMTP( 'mailgate.sandia.gov' )
		server.sendmail( fromaddr, toaddr, self.FormatMessage( Headers, msg ) )
		server.quit()

	def FormatMessage( self, headers, msg ):
		return string.join( map( lambda x: '%s: %s\r\n' % x, headers.items() ), '' ) + '\r\n' + msg
		
	def __repr__( self ):
		return 'mailto://' + self.Address
