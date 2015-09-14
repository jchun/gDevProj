#!/Library/Frameworks/Python.framework/Versions/2.7/bin/python

'''
Created by Joseph Chun
August 27th 2015
'''
import argparse
from bs4 import BeautifulSoup
import calendar
import datetime
import os
import re
import time
import urllib2

calendarPage = 'http://www.levisstadium.com/events/category/tickets/'
months = {v: k for k,v in enumerate(calendar.month_abbr)}
savedLocalEvents = {}

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
            hourString = str(int(hourString) + 12)
        timeString = hourString + ':' + minuteString
        
        dateTimeString = dateString + ' - ' + timeString
        dateTimeStruct = time.strptime(dateTimeString, "%Y/%m/%d - %H:%M")
        eventDateTime = time.strftime("%G-%m-%dT%H:%M:00", dateTimeStruct)
        return eventDateTime
    else:
        print 'ERROR - Cannot handle time string: ' + date
        return None

def parseEvent(eventLink):
    '''
    Parse the individual event page
    '''
    eventSoup = soupIt(eventLink)
   
    titleInfo = eventSoup.findAll('h1', { 'class' : 'page-title' })

    if not titleInfo:
        print 'No title found, skipping add'
        
    else:
        title = titleInfo[0].string.strip()

    dateInfo = eventSoup.findAll('div', { 'class' : 'date' })

    if not dateInfo:
        print 'No dates found, skipping add'
        
    else:
        for dateField in dateInfo:
            date = dateField.findAll('span', { 'class' : 'text' })    
        date = date[0].string
    
    #following block is for debugging purposes
    ''' 
    print '*' * 15
    print title
    print date
    print eventLink
    print '*' * 15
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
    events = calSoup.findAll('article')
    
    if not events:
        print 'No events found'
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
        print 'Finishing up'
        return
    else:
        nextPage = nextNav[0].findAll('a', href=True)
        if not nextPage:
            '''
            Finished iterating through all events calendar pages
            '''
            print 'Finishing up'
            return
        nextUrl = nextPage[0]['href']
        parseCalendar(nextUrl)
        return

def soupIt(url):
    '''
    Given a url, generate and return the BeautifulSoup
    '''
    try:
        u = urllib2.urlopen(url, timeout=3)
        soup = BeautifulSoup(u, 'html.parser')
        return soup
    except urllib2.URLError, e:
        raise NameError('URL Request Error')

def main():
    parseCalendar(calendarPage)

if __name__ == '__main__':
    startTime = time.time()
    
    #'''
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output')
    parser.add_argument('-v', dest='verbose', action='store_true')
    args = parser.parse_args()
    
    #print 'args: ' + str(args)
    #'''
   
    main()    

    print 'Time taken: ' + str(time.time()-startTime) + ' secs'
