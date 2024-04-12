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


def isWeekend(timezone='Australia/Sydney'):
    localDT = datetime.datetime.now(pytz.timezone(timezone))
    if ((dayOfWeekMap[localDT.weekday()] == 'Saturday' and localDT.time() > datetime.time(8, 5)) or (
            dayOfWeekMap[localDT.weekday()] == 'Monday' and localDT.time() < datetime.time(7, 55)) or
            (dayOfWeekMap[localDT.weekday()] == 'Sunday')):
        return True
    return False


schedule.every().monday.at("07:55").do(startWeeklyJobs)
schedule.every().saturday.at("08:05").do(clearWeeklyJobs)

lg.info("Starting scheduler...")
if not isWeekend():
    startWeeklyJobs()

while True:
    schedule.run_pending()
