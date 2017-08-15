#! /usr/bin/env python3
import logging
import os
import sys
import time

filesRemoved = 0

if not os.path.exists('logs'):
    os.makedirs('logs')
logFileName = 'logs/' + time.strftime("levisCal_%Y_%m_%d_%H_%M_%S.log")
logging.basicConfig(filename=logFileName,\
                    level=logging.INFO)
logger = logging.getLogger(__name__)

def oldestLogFile(path, extension=".log"):
    return min(
        (os.path.join(dirname, filename)
        for dirname, dirnames, filenames in os.walk(path)
        for filename in filenames
        if filename.endswith(extension)),
        key=lambda fn: os.stat(fn).st_mtime)

def deleteOlderThanXDays(days, path):
    now = time.time()
    for f in os.listdir(path):
        f = os.path.join(path, f)
        if os.stat(f).st_mtime < now - (days * 86400):
            if os.path.isfile(f) and f.endswith(extension):
                logging.info('Deleting old log file ' + str(f))
                os.remove(os.path.join(path, f))
                filesRemoved += 1

def main(path='logs'):
    logging.info('Starting log cleanup at path: \'%s\'', path)
    deleteOlderThanXDays(30, path)
    logging.info('Removed %d files' % filesRemoved)

if __name__ == '__main__':
    main()
