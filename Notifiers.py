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
__version__ = '$Revision: 5 $a'[11:-2]
__svnauthor__ = '$Author: Jaraco $'[9:-2]
__date__ = '$Date: 04-07-13 13:45 $'[7:-2]

import string
import smtplib, socket

class Notifier( object ):
	def write( self, msg ):
		self.Notify( msg )
		
class SMTPMailbox( Notifier ):
	def __init__( self, address, server = 'mailgate.sandia.gov' ):
		self.Address = address
		self.Server = server

	def Notify( self, msg = '', importance = 'Normal' ):        
		import smtplib
		fromaddr = 'SMTP Notifier <notifier@%s>' % socket.getfqdn()
		toaddr = self.Address
		Headers = { 'From': fromaddr, 'To': toaddr, 'Importance':importance, 'Subject':'Notification' }

		server = smtplib.SMTP( self.Server )
		server.sendmail( fromaddr, toaddr, self.FormatMessage( Headers, msg ) )
		server.quit()

	def FormatMessage( self, headers, msg ):
		msg = msg.encode( 'ascii', 'replace' )
		return string.join( map( lambda x: '%s: %s\r\n' % x, headers.items() ), '' ) + '\r\n' + msg

	def __repr__( self ):
		return 'mailto://' + self.Address
