from pyConfig import *
from modules import utility, gmail


def detectAFBIPositions(cfg):
    refData = utility.loadRefData()
    dfPositions = pullAFBIPositions()
    positions = {}
    for sym in cfg['targets']:
        bbSym = refData.loc[sym]['iqfSym']
        if bbSym not in dfPositions['BB Yellow Key'].values:
            positions[sym] = 0
            lg.info(f"Can't find a {sym} position from AFBI, initialising at 0 for now...")
        else:
            positions[sym] = dfPositions.loc[dfPositions['BB Yellow Key'] == bbSym]['Active']

    return positions


def pullAFBIPositions():
    lg.info("Pulling Latest AFBI Positions..")
    afbiCredentials = interfaceRoot + "credentials.json"
    afbiToken = interfaceRoot + "token.json"
    afbiEmailRegex = "CBCT EOD POSITIONS"

    service = gmail.get_gmail_service(afbiCredentials, afbiToken)
    latestEmail = gmail.pullLatestPosFile(service, afbiEmailRegex)
    print('Latest AFBI Position File: ' + latestEmail['filename'])
    return latestEmail['data']
