#! /usr/bin/env python3

'''
Created by Joseph Chun
August 27th 2015
'''
from bs4 import BeautifulSoup
import calendar
import datetime
import os
import re
import time
import urllib3
import logging

''' Logging '''
if not os.path.exists('logs'):
    os.makedirs('logs')
logFileName = 'logs/' + time.strftime("levisCal_%Y_%m_%d_%H_%M_%S.log")
logging.basicConfig(filename=logFileName,\
                    level=logging.INFO)
logger = logging.getLogger(__name__)

''' Globals '''
calendarPage = 'http://www.levisstadium.com/events/category/tickets/'
months = {v: k for k,v in enumerate(calendar.month_abbr)}
savedLocalEvents = {}

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def cleanDate(date):
    '''
    Take date string on website and format it
    '''
    dateSplit = date.split()

    if len(dateSplit) == 3:
        '''there is no time, only date'''
        eventMonth = months[dateSplit[0][0:3]]
        eventDay = int(re.sub('[^0-9]','', date.split()[1]))
        eventYear = int(dateSplit[2])
        eventDateTime = datetime.date(eventYear, eventMonth, eventDay).isoformat()
        return eventDateTime

    elif len(dateSplit) > 3:
        eventMonth = months[dateSplit[0][0:3]]
        eventDay = int(re.sub('[^0-9]','', date.split()[1]))
        eventYear = int(dateSplit[2])
        dateString = str(eventYear) + '/' + str(eventMonth) + '/' + str(eventDay)
        
        hourString, minuteString = str(dateSplit[4]).split(':')
        if dateSplit[5] == 'pm':
            if int(hourString) != 12:
                hourString = str(int(hourString) + 12)
        timeString = hourString + ':' + minuteString
        
        dateTimeString = dateString + ' - ' + timeString
        dateTimeStruct = time.strptime(dateTimeString, "%Y/%m/%d - %H:%M")
        eventDateTime = time.strftime("%Y-%m-%dT%H:%M:00", dateTimeStruct)
        return eventDateTime
    else:
        print(bcolors.FAIL + 'ERROR - Cannot handle time string: ' + date + \
                bcolors.ENDC)
        logger.error('Cannot handle time string: ' + date)
        return None

def parseEvent(eventLink):
    '''
    Parse the individual event page
    '''
    eventSoup = soupIt(eventLink)
    if eventSoup is None:
        return
   
    titleInfo = eventSoup.findAll('h1', { 'class' : 'page-title' })

    if not titleInfo:
        print(bcolors.FAIL + 'No title found, skipping add' + \
                bcolors.ENDC)
        logger.warning('No title found, skipping add')
        
    else:
        title = titleInfo[0].string.strip()

    dateInfo = eventSoup.findAll('div', { 'class' : 'date' })

    if not dateInfo:
        print(bcolors.FAIL + 'No dates found, skipping add' + \
                bcolors.ENDC)
        logger.warning('No dates found, skipping add')
        
    else:
        for dateField in dateInfo:
            date = dateField.findAll('span', { 'class' : 'text' })    
        date = date[0].string
    
    #following block is for debugging purposes
    ''' 
    print('*' * 15)
    print(title)
    print(date)
    print(eventLink)
    print('*' * 15)
    '''

    date = cleanDate(date)
    parsedEvent = date, eventLink
    '''
    We store the event info in this dictionary,
    which will be accessed from levisEventsCoordinator.py
    '''
    savedLocalEvents[title] = parsedEvent


def parseCalendar(calendarLink):
    '''
    Parse the main events page
    '''
    calSoup = soupIt(calendarLink)
    if calSoup is None:
        return

    events = calSoup.findAll('article')
    
    if not events:
        print(bcolors.FAIL + 'No events found' + bcolors.ENDC)
        logger.info('No events found')
        return
    
    else:
        for event in events:
            links = event.findAll('a', href=True)
            eventLink = links[1]['href']
            parseEvent(eventLink)
    
    nextNav = calSoup.findAll('div', {'class' : 'nav-next events-nav-newer'})
    if not nextNav:
        '''
        I think every page has a nav-next element
        so we shouldn't hit this
        '''
        #print('Finishing up')
        return
    else:
        nextPage = nextNav[0].findAll('a', href=True)
        if not nextPage:
            '''
            Finished iterating through all events calendar pages
            '''
            #print('Finishing up')
            return
        nextUrl = nextPage[0]['href']
        parseCalendar(nextUrl)
        return

def soupIt(url):
    '''
    Given a url, generate and return the BeautifulSoup
    '''
    try:
        http = urllib3.PoolManager()
        response = http.request('GET', url)
        soup = BeautifulSoup(response.data, "html.parser")
        return soup
    except urllib3.exceptions.TimeoutError:
        print(bcolors.FAIL + 'Timeout Error: ' + url + bcolors.ENDC)
        logger.critical('Timeout Error: ' + url)
        '''
        raise NameError('Timeout Error')
        '''
        return None

def main():
    logger.info('Parsing: ' + calendarPage)
    parseCalendar(calendarPage)
    logger.info('Finished parsing')

if __name__ == '__main__':
    startTime = time.time()
    
    main()    

    print(bcolors.OKBLUE + \
            'Time taken: ' + str(time.time()-startTime) + ' secs' +\
            bcolors.ENDC)
    logger.info('Time taken: ' + str(time.time()-startTime) + ' secs')

