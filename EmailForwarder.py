# -*- coding: UTF-8 -*-

"""EmailForwarder
A service that when coupled with Microsoft Windows Server
2003 e-mail service will forward messages based on an aliases
file in /etc/aliases -based format.

aliases.txt should be placed in the mailroot folder
	
Copyright © 2004 Sandia National Laboratories  
"""

__author__ = 'Jason R. Coombs <jaraco@sandia.gov>'
__version__ = '$Revision: 2 $'[11:-2]
__vssauthor__ = '$Author: Jaraco $'[9:-2]
__date__ = '$Modtime: 04-06-23 12:21 $'[10:-2]

import win32service, win32serviceutil, win32event
import email, smtplib, os, sys
import etcalias, tools, FileChange

import logging
log = logging.getLogger( 'Processing Service' )

mailroot = r'c:\InetPub\mailroot'

class TheService( win32serviceutil.ServiceFramework ):
	_svc_name_ = 'EmailForwarding'
	_svc_display_name_ = 'E-mail Forwarding Service'

	def __init__( self, args ):
		win32serviceutil.ServiceFramework.__init__( self, args )

	def SvcStop( self ):
		self.ReportServiceStatus( win32service.SERVICE_STOP_PENDING )
		self.notifier.Quit()

	def SvcDoRun( self ):
		import servicemanager

		self.setupLogging()

		log.info( '%s service is starting.', self._svc_display_name_ )
		servicemanager.LogMsg(
			servicemanager.EVENTLOG_INFORMATION_TYPE,
			servicemanager.PYS_SERVICE_STARTED,
			(self._svc_name_, '' )
			)

		self.run()

		servicemanager.LogMsg(
			servicemanager.EVENTLOG_INFORMATION_TYPE,
			servicemanager.PYS_SERVICE_STOPPED,
			( self._svc_name_, '' )
			)
		log.info( '%s service is stopped.', self._svc_display_name_ )

	def run( self ):
		aliasFile = os.path.join( mailroot, 'aliases.txt' )
		aliases = self.loadAliases( aliasFile )
		dropFolder = os.path.join( mailroot, 'Drop' )
		self.notifier = FileChange.BlockingNotifier( dropFolder )
		self.notifier.filters.append( FileChange.PatternFilter( '*.eml' ) )
		for newEmail in self.notifier.GetChangedFiles():
			if os.path.exists( newEmail ):
				log.info( 'New e-mail message received: %s', newEmail )
				try:
					msg = email.message_from_file( file( newEmail ) )
					fromAddress = msg[ 'X-sender' ]
					alias = msg[ 'X-receiver' ]
					del msg[ 'X-sender' ]
					del msg[ 'X-receiver' ]
					log.debug('Alias is %s; from address is %s.', alias, fromAddress )
					if aliases.has_key( alias ):
						smtp = smtplib.SMTP()
						smtp.connect()
						# smtp.login( 'SMTPRelayUser', 'smtppass' )
						# log.info( 'Would be sending message %s', msg )
						smtp.sendmail( fromAddress, aliases[alias], msg.as_string() )
						#os.remove( newEmail )
					else:
						log.info( 'Ignoring message %s: receiver address %s not found in aliases file.', newEmail, alias )
				except:
					log.exception( 'Exception while attempting to process a new e-mail message in %s.', newEmail )
				# move file to archive
				dirname = os.path.dirname( newEmail )
				basename = os.path.basename( newEmail )
				os.renames( newEmail, os.path.join( dirname, 'Archive', basename ) )
			else:
				log.warning( 'Notification was received of changed file, but now it doesn\'t exist (%s).', newEmail )

	def loadAliases( self, aliasFile ):
		f = file( aliasFile ).read()
		aliases = etcalias.parse( 'aliasList', f )
		if not aliases:
			aliases = []
			log.critical( 'No aliases were parsed from the aliases file' )
		return dict( aliases )

	def setupLogging( self ):
		logfile = os.path.join( os.environ['WINDIR'], 'system32', 'LogFiles', 'Email Forwarding', 'Log.log' )
		handler = tools.TimestampFileHandler( logfile )
		handlerFormat = '[%(asctime)s] - %(levelname)s - [%(name)s] %(message)s'
		handler.setFormatter( logging.Formatter( handlerFormat ) )
		logging.root.addHandler( handler )
		# if I don't redirect stdoutput and stderr, when the stdio flushes,
		#  an exception will be thrown and the service will bail
		sys.stdout = tools.LogFileWrapper( 'stdout' )
		sys.stderr = tools.LogFileWrapper( 'stderr' )
		logging.root.level = logging.INFO

if __name__ == '__main__':
	win32serviceutil.HandleCommandLine( TheService )
