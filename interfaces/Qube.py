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
    dfPositions = pullQubePositions(gmailService)
    notDetected = []
    positions = {}
    for sym in cfg['targets']:
        qubeSym = findQubeTradedSym(sym)
        if qubeSym in dfPositions['BBG'].values:
            row = np.where(dfPositions['BBG'] == qubeSym)[0][0]
            positions[sym] = int(dfPositions.iloc[row]['Position EOD USD'])
        else:
            notDetected.append(sym)
            positions[sym] = 0

    if len(notDetected) != 0:
        lg.info(f"No Qube Positions Detected For {notDetected}, Initialising At 0.")
    return positions


def pullQubePositions(gmailService):
    latestEmail = gmail.pullLatestPosFile(gmailService, searchQuery="Qube", fileQuery="QQSec_Detailed_CB")
    lastPosTime = findEmailTime(latestEmail['filename'])
    utility.logPositionDelay(lastPosTime, timezone, investor='Qube')
    return latestEmail['data']


def findEmailTime(filename):
    for s in ['QQSec_Detailed_CB_', '.xlsx']:
        filename = filename.replace(s, '')
    return pd.Timestamp(filename)

def findQubeTradedSym(sym):
    refData = utility.loadRefData()
    return refData.loc[refData['iqfUnadjusted'] == sym]['qubeTradedSym'].values[0]
