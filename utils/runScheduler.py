import sys

sys.path.insert(0, "C:/Users/matth/PycharmProjects/SydneyQuantitative/csaProd/")
# sys.path.insert(0, "C:/Users/Owner/Desktop/CBCT/code/")

from pyConfig import *
import schedule

lg.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=lg.INFO, datefmt='%H:%M:%S')


def callRunLive():
    lg.info("Calling runLive...")
    exec(open('runLive.py').read())
    return


def startWeeklyJobs():
    lg.info("Starting Weekly Jobs...")
    schedule.every().hour.at(":00").do(callRunLive).tag('weekly')
    return


def clearWeeklyJobs():
    lg.info("Clearing Weekly Jobs...")
    schedule.clear('weekly')
    return


def dummyJob():
    lg.info("Running dummyJob")
    return


schedule.every().monday.at("08:55").do(startWeeklyJobs)
schedule.every().saturday.at("08:05").do(clearWeeklyJobs)

lg.info("Starting scheduler...")
while True:
    startWeeklyJobs()
    schedule.run_pending()
