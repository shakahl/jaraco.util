# -*- coding: UTF-8 -*-

"""Notifiers
	Classes for notifying in the case of an event.

	All objects should support the .write method to append data and
	.Notify to send the message.

	Objects:
		SMTPMailbox - sends a message to an SMTP mailbox upon
			notification.
			
Copyright © 2004 Sandia National Laboratories  
"""

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Revision: 3 $a'[11:-2]
__vssauthor__ = '$Author: Jaraco $'[9:-2]
__date__ = '$Modtime: 04-06-23 12:27 $'[10:-2]

import string
import smtplib, socket

class Notifier( object ):
	def write( self, msg ):
		self.Notify( msg )
		
class SMTPMailbox( Notifier ):
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
