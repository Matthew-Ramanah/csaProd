from pyConfig import *
from modules import utility, gmail
from interfaces import common

timezone = 'US/Eastern'

mannedHours = {
    "Monday": [13],
    "Tuesday": [13],
    "Wednesday": [13],
    "Thursday": [13],
    "Friday": [13],
    "Saturday": [],
    "Sunday": []
}


def isDeskManned():
    localDT = datetime.datetime.now(pytz.timezone(timezone))
    localDay = dayOfWeekMap[localDT.weekday()]
    if localDT.hour in mannedHours[localDay]:
        return True
    else:
        return False


def detectQubePositions(cfg, gmailService):
    positions = {}
    for sym in cfg['targets']:
        positions[sym] = 0
    return positions
