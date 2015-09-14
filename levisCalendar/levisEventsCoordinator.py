from apiclient import discovery
import datetime
import httplib2
import oauth2client
from oauth2client import client
from oauth2client import tools
import os
import time

import levisParser
savedLocalEvents = levisParser.savedLocalEvents
savedRemoteEvents = {}

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
        print 'Storing credentials to ' + credential_path
    return credentials

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
    print 'Event created: %s' % (gEvent.get('htmlLink'))

numRuns = 0
 
def getEvents(service, numEvents):
    global numRuns
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print 'Getting the upcoming %d events' % (numEvents)
    eventsResult = service.events().list(
        calendarId='ahr56gto4a44e4uj2bumer2h5k@group.calendar.google.com', timeMin=now, maxResults=numEvents, singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])

    if not events:
        print 'No upcoming events found.'
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        if (numRuns % 2) != 0:
            print start, event['summary']
        savedRemoteEvents[event['summary']] = start
    numRuns += 1

def main():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)
    
    getEvents(service, 100) 

    levisParser.main()
    for (eventTitle, eventInfo)  in savedLocalEvents.items():
        eventDateTime, eventURL = eventInfo
        
        if eventTitle not in savedRemoteEvents:
            createEvent(service, eventDateTime, eventTitle, eventURL)
        else:
            #print 'Skipping add, we already know this event!'    
            continue

    getEvents(service, 100) 

if __name__ == '__main__':
    startTime = time.time()
    main()
    print 'Time taken: ' + str(time.time()-startTime) + ' secs'
