#! /usr/bin/env python3

from apiclient import discovery
import datetime
import httplib2
import oauth2client
from oauth2client import client
from oauth2client import tools
import os
import re
import smtplib
import time

import levisParser
from levisParser import bcolors
savedLocalEvents = levisParser.savedLocalEvents
savedRemoteEvents = {}
newEvents = []

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Levi\'s Stadium Events Coordinator'

def get_credentials():
    """
    This function is from Google's quickstart tutorial
    Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-quickstart.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatability with Python 2.6
            credentials = tools.run(flow, store)
        print(bcolors.WARNING + 'Storing credentials to ' + credential_path +\
                bcolors.ENDC)
    return credentials

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
    return message

def sendEmail():
    events_info = constructEmail()

    if not events_info:
        print("No new events have been created, no need to email")
        return

    to = 'joeyeatsspam@gmail.com' 
    gmail_user = 'joeyalerter@gmail.com'
    gmail_pwd = '***' #@TODO replace password
    smtpserver = smtplib.SMTP("smtp.gmail.com",587)
    # identify ourselves to smtp gmail client
    smtpserver.ehlo()
    # secure our email with tls encryption
    smtpserver.starttls()
    # re-identify ourselves as an ecrypted connection
    smtpserver.ehlo()
    smtpserver.login(gmail_user, gmail_pwd)
    header = 'To:' + to + '\n' + 'From: ' + gmail_user + '\n' + \
             'Subject: Levi\'s Stadium Event Notification\n'
    
    msg_intro = 'Here are some new upcoming events: \n'
    
    content =  msg_intro + events_info 
    
    msg = header + '\n' + content

    #print(msg) #@TODO debug print
    smtpserver.sendmail(gmail_user, to, msg) #@TODO comment out to disable send
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
              {'method': 'popup', 'minutes': 10},
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
              {'method': 'popup', 'minutes': 10},
            ],
          },
        }
  
    gEvent = service.events().insert(calendarId='ahr56gto4a44e4uj2bumer2h5k@group.calendar.google.com', body=event).execute()
    # Lets add the new event to the newEvent list in case we want to email it out
    newEvent = (eventDateTime, eventTitle, eventURL, gEvent.get('htmlLink'))
    newEvents.append(newEvent)

    # Print to console
    print(bcolors.OKGREEN + bcolors.BOLD + \
            'Event created: %s - %s' % (eventDateTime, eventTitle) +\
            bcolors.ENDC)
    print(bcolors.OKGREEN + bcolors.UNDERLINE + eventURL)
    print(gEvent.get('htmlLink') + bcolors.ENDC)

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
        calendarId='ahr56gto4a44e4uj2bumer2h5k@group.calendar.google.com', timeMin=now, maxResults=numEvents, singleEvents=True,
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

def main():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)
    
    getEvents(service, 100) 

    levisParser.main()
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
                    ''' Lets delete the old event before creating new '''
                    print('Deleting old event...')
                    service.events().delete(calendarId='ahr56gto4a44e4uj2bumer2h5k@group.calendar.google.com', eventId=remoteId).execute()
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
                    ''' Lets delete the old event before creating new '''
                    print('Deleting old event...')
                    service.events().delete(calendarId='ahr56gto4a44e4uj2bumer2h5k@group.calendar.google.com', eventId=remoteId).execute()
                    createEvent(service, eventDateTime, eventTitle, eventURL)

    getEvents(service, 100) 
    sendEmail()

if __name__ == '__main__':
    startTime = time.time()
    main()
    print(bcolors.OKBLUE + \
            'Time taken: ' + str(time.time()-startTime) + ' secs' + \
            bcolors.ENDC)
