#! /usr/bin/env python3
'''
Created by Joseph Chun
September 8th 2015
'''
''' Basic Libs '''
import datetime
import os
import re
import smtplib
import time
''' Config-related '''
import configparser
import errno
import sys
''' parser-related '''
import parser
from parser import bcolors
savedLocalEvents = parser.savedLocalEvents
savedRemoteEvents = {}
newEvents = []
''' Logging '''
import logging
import logManager
logsPath = 'logs'
if not os.path.exists(logsPath):
    os.makedirs(logsPath)
logFileName = logsPath + '/' + time.strftime("levisCal_%Y_%m_%d_%H_%M_%S.log")
logging.basicConfig(filename=logFileName,\
                    level=logging.INFO)
logger = logging.getLogger(__name__)
''' required for Google-API '''
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

''' Google API Stuff '''
# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def getCredentials():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds


def constructEmail():
    message = ''
    for event in newEvents:
        eventDateTime, eventTitle, eventURL, htmlLink = event
        message += '\n\n'
        message += (eventTitle + ' - ' + \
                    eventDateTime + '\n' + \
                    eventURL + '\n' + \
                    htmlLink + '\n')
    # following line we replace en-dash with hypens due to 
    # ascii encoding (not) supported for en-dash on smtplib
    message = re.sub(u"\u2013", "-", message)
    message = re.sub(u"\u2019", "'", message)
    return message

def sendEmail():
    events_info = constructEmail()

    if not events_info:
        print("No new events have been created, no need to email")
        logger.info("No new events have been created, no need to email")
        return

    to = RECIPIENT_EMAIL
    gmail_user = ALERTER_EMAIL
    gmail_pwd = ALERTER_PASSWORD
    smtpserver = smtplib.SMTP("smtp.gmail.com",587)
    # identify ourselves to smtp gmail client
    smtpserver.ehlo()
    # secure our email with tls encryption
    smtpserver.starttls()
    # re-identify ourselves as an ecrypted connection
    smtpserver.ehlo()

    ''' Login to Server '''
    try:
        smtpserver.login(gmail_user, gmail_pwd)
    except smtplib.SMTPAuthenticationError:
        print(bcolors.FAIL + 'Failed sending email, check Alerter '
              '& AlerterPwd fields in settings.conf' + bcolors.ENDC)
        logger.error('Failed sending email, check Alerter '
                     '& AlerterPwd fields in settings.conf')
        smtpserver.close()
        return
    
    ''' Finish filling in all fields of email '''
    header = 'To:' + to + '\n' + 'From: ' + gmail_user + '\n' + \
             'Subject: Levi\'s Stadium Event Notification\n'
    msg_intro = 'Here are some new upcoming events: \n'
    content =  msg_intro + events_info 
    msg = header + '\n' + content
    ''' Send Email, then close connection '''
    smtpserver.sendmail(gmail_user, to, msg) 
    smtpserver.close()

def createEvent(service, eventDateTime, eventTitle, eventURL):
    if 'T' in eventDateTime:
        '''
        Assumptions in scheduling:
        1. Events will be apx 4 hours long
        2. No event will start later than 11PM
        '''
        eventEndDateHour = 4 + int(eventDateTime.split('T')[1].split(":",1)[0])
        if eventEndDateHour >= 24:
            eventEndDateHour = 23
        eventEndDateTime = eventDateTime.rsplit('T')[0] + 'T' + \
                           str(eventEndDateHour) + ':' + \
                           eventDateTime.split('T')[1].split(":",1)[1]

        event = {
          'summary': eventTitle,
          'location': '4900 Marie P Bartolo Way, Santa Clara, CA 95054',
          'description': eventURL,
          'start': {
            'dateTime': eventDateTime,
            'timeZone': 'America/Los_Angeles',
          },
          #'''
          'end': {
            'dateTime': eventEndDateTime,
            'timeZone': 'America/Los_Angeles',
          },
          #'''
          'reminders': {
            'useDefault': False,
            'overrides': [
              {'method': 'popup', 'minutes': 180},
            ],
          },
        }
    else:
        event = {
          'summary': eventTitle,
          'location': '4900 Marie P Bartolo Way, Santa Clara, CA 95054',
          'description': eventURL,
          'start': {
            'date': eventDateTime,
            'timeZone': 'America/Los_Angeles',
          },
          #'''
          'end': {
            'date': eventDateTime,
            'timeZone': 'America/Los_Angeles',
          },
          #'''
          'reminders': {
            'useDefault': False,
            'overrides': [
              {'method': 'popup', 'minutes': 180},
            ],
          },
        }
  
    gEvent = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    # Lets add the new event to the newEvent list in case we want to email it out
    newEvent = (eventDateTime, eventTitle, eventURL, gEvent.get('htmlLink'))
    newEvents.append(newEvent)

    # Print to console
    print(bcolors.OKGREEN + bcolors.BOLD + \
            'Event created: %s - %s' % (eventDateTime, eventTitle) +\
            bcolors.ENDC)
    print(bcolors.OKGREEN + bcolors.UNDERLINE + eventURL)
    print(gEvent.get('htmlLink') + bcolors.ENDC)

    logger.info('Event created: %s - %s' % \
                (eventDateTime, eventTitle))
    logger.info(eventURL)
    logger.info(gEvent.get('htmlLink'))

'''
Purpose of numRuns is to keep track of which time this was called
During 0th call, we use it only to fetch (and not print) existing calendar
During 1st call, we use it to fetch & print updated/existing calendar
getEvents function assumes it will be called exactly twice for those purposes
'''
numRuns = 0
 
def getEvents(service, numEvents):
    global numRuns
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    if (numRuns %2) != 0:
        print(bcolors.OKBLUE + 'Fetching the upcoming %d events' % (numEvents) +\
                bcolors.ENDC)
        print('*' * 15)
    eventsResult = service.events().list(
        calendarId=CALENDAR_ID, timeMin=now, maxResults=numEvents, singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])

    if not events:
        print('No upcoming events found.')
    for event in events:
        eventTitle = event['summary']
        eventStart = event['start'].get('dateTime', event['start'].get('date'))
        eventURL = event['description']
        eventId = event['id']
        if (numRuns % 2) != 0:
            print(eventStart, eventTitle)
            print(eventURL)
            print('*' * 15)
        savedRemoteEvents[eventURL] = eventTitle, eventStart, eventId
    numRuns += 1

def loadConfig():
    global LOGGING_LEVEL
    global CLIENT_SECRET_FILE
    global RECIPIENT_EMAIL
    global ALERTER_EMAIL
    global ALERTER_PASSWORD
    global CALENDAR_ID

    configError = False

    defaultConfig = {'LoggingLevel': 'info',
                     'ClientSecretFile' : 'client_secret.json',}
    config = configparser.ConfigParser(defaultConfig)
    config.read('settings.conf')

    '''
    Following fields have default values in source code,
    Safe to read without a try/except if/else
    '''
    LOGGING_LEVEL =      config['FILEINFO']['LoggingLevel']
    CLIENT_SECRET_FILE = config['FILEINFO']['ClientSecretFile']

    '''
    Following are critical fields from settings.conf
    Exit if any of these fields are not set
    @TODO: add error checking for format of config options
    '''
    ''' Recipient '''
    if config.has_option('USERINFO', 'Recipient'):
        RECIPIENT_EMAIL = config['USERINFO']['Recipient']
    else:
        configError = True
        print('No Recipient specified in settings.conf!')
        logger.error('No Recipient specified in settings.conf!')
    ''' Alerter '''
    if config.has_option('USERINFO', 'Alerter'):
        ALERTER_EMAIL = config['USERINFO']['Alerter']
    else:
        configError = True
        print('No Alerter specified in settings.conf!')
        logger.error('No Alerter specified in settings.conf!')
    ''' AlerterPwd '''
    if config.has_option('USERINFO', 'AlerterPwd'):
        ALERTER_PASSWORD = config['USERINFO']['AlerterPwd']
    else:
        configError = True
        print('No AlerterPwd specified in settings.conf!')
        logger.error('No AlerterPwd specified in settings.conf!')
    ''' CalendarId '''
    if config.has_option('USERINFO', 'CalendarId'):
        CALENDAR_ID = config['USERINFO']['CalendarId']
    else:
        configError = True
        print('No CalendarId specified in settings.conf!')
        logger.error('No CalendarId specified in settings.conf!')

    ''' Exit if any of the critical fields are missing from settings.conf '''
    if configError:
        print('Exiting...')
        logger.error('Exiting...')
        sys.exit(errno.EINVAL)

    logger.info('LOGGING_LEVEL=%s'      % LOGGING_LEVEL)
    logger.info('CLIENT_SECRET_FILE=%s' % CLIENT_SECRET_FILE)
    logger.info('RECIPIENT_EMAIL=%s'    % RECIPIENT_EMAIL)
    logger.info('ALERTER_EMAIL=%s'      % ALERTER_EMAIL)
    logger.info('ALERTER_PASSWORD=%s'   % ALERTER_PASSWORD)
    logger.info('CALENDAR_ID=%s'        % CALENDAR_ID)


def main():
    ''' Logging housekeeping '''
    logManager.main(logsPath)
    ''' Load config '''
    loadConfig()
    ''' Set LoggingLevel set in settings.conf '''
    logger.setLevel(LOGGING_LEVEL)
    logger.info('Logger level set to %s', LOGGING_LEVEL)
    ''' Grab credentials '''
    creds = getCredentials()
    service = build('calendar', 'v3', credentials=creds)
    
    ''' Grab events from calendar '''
    getEvents(service, 100) 

    ''' Parse website '''
    parser.main()

    ''' Process results from parsing '''
    for (eventTitle, eventInfo) in savedLocalEvents.items():
        eventDateTime, eventURL = eventInfo
        if eventURL not in savedRemoteEvents:
            ''' We might already know the event, see if we should update '''
            ''' See if we match any of our existing event names '''
            for (remoteURL, remoteInfo) in savedRemoteEvents.items():
                remoteTitle, remoteStart, remoteId = remoteInfo
                ''' we're not support checking matching time yet '''
                if (remoteTitle == eventTitle): #or (remoteStart == eventDateTime):
                    print(bcolors.OKGREEN + 'Update the following event:')
                    print(remoteTitle + ', ' + remoteStart + bcolors.ENDC)
                    logger.info('Update the following event:')
                    logger.info(remoteTitle + ', ' + remoteStart)
                    ''' Lets delete the old event before creating new '''
                    print('Deleting old event...')
                    logger.info('Deleting old event...')
                    service.events().delete(calendarId=CALENDAR_ID, eventId=remoteId).execute()
                    break
            createEvent(service, eventDateTime, eventTitle, eventURL)
        else:
            ''' We have the URL of the event '''
            ''' but we may need to update '''
            if 'T' in eventDateTime:
                ''' Check if there is a time added to the Events Page '''
                remoteTitle, remoteStart, remoteId = savedRemoteEvents[eventURL]
                if 'T' not in remoteStart:
                    print(bcolors.OKGREEN + 'Update the time of following event: ')
                    print(remoteTitle + ', ' + remoteStart + bcolors.ENDC)
                    logger.info('Update the time of the following event: ')
                    logger.info(remoteTitle + ', ' + remoteStart)
                    ''' Lets delete the old event before creating new '''
                    print('Deleting old event...')
                    logger.info('Deleting old event...')
                    service.events().delete(calendarId=CALENDAR_ID, eventId=remoteId).execute()
                    createEvent(service, eventDateTime, eventTitle, eventURL)

    getEvents(service, 100) 
    sendEmail()

if __name__ == '__main__':
    startTime = time.time()

    main()
    print(bcolors.OKBLUE + \
            'Time taken: ' + str(time.time()-startTime) + ' secs' + \
            bcolors.ENDC)
    logger.info('Time taken: ' + str(time.time()-startTime) + ' secs')
