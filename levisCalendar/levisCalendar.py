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

import gCalendar

calendarPage = 'http://www.levisstadium.com/events/category/tickets/'
months = {v: k for k,v in enumerate(calendar.month_abbr)}

def cleanDate(date):
    dateSplit = date.split()
    eventMonth = months[dateSplit[0][0:3]]
    eventDay = int(re.sub('[^0-9]','', date.split()[1]))
    eventYear = int(dateSplit[2])
    eventTime = '0:00'

    return (eventMonth, eventDay, eventYear, eventTime)

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
    
    ''' 
    print '*' * 15
    print title
    print date
    print months[date[0:3]]
    print eventLink
    print '*' * 15
    '''

    date = cleanDate(date)

    parsedEvent = title, date, eventLink
    print parsedEvent
    return parsedEvent



def parseCalendar(calendarLink):
    '''
    Parse the main events page
    '''
    calSoup = soupIt(calendarPage)
    events = calSoup.findAll('article')
    
    if not events:
        print 'No events found'
        return
    
    else:
        for event in events:
            links = event.findAll('a', href=True)
            eventLink = links[1]['href']
            parseEvent(eventLink)
            '''@TODO remove following break:'''

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


if __name__ == '__main__':
    startTime = time.time()
    
    #'''
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output')
    parser.add_argument('-v', dest='verbose', action='store_true')
    args = parser.parse_args()
    
    #print 'args: ' + str(args)
    #'''
   
    parseCalendar(calendarPage)
        
    #gCalendar.main()

    print 'Time taken: ' + str(time.time()-startTime) + ' secs'
