from pyConfig import *
from modules import utility, gmail
from interfaces import common

timezone = 'US/Eastern'

mannedHours = {
    "Monday": [0, 1, 2, 3, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
    "Tuesday": [0, 1, 2, 3, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
    "Wednesday": [0, 1, 2, 3, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
    "Thursday": [0, 1, 2, 3, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
    "Friday": [0, 1, 2, 3, 8, 9, 10, 11, 12, 13, 14, 15, 16],
    "Saturday": [],
    "Sunday": [18, 19, 20, 21, 22, 23]
}


def isDeskManned():
    localDT = datetime.datetime.now(pytz.timezone(timezone))
    localDay = dayOfWeekMap[localDT.weekday()]
    if localDT.hour in mannedHours[localDay]:
        return True
    else:
        return False


def detectAFBIPositions(cfg, gmailService):
    dfPositions = pullAFBIPositions(gmailService)
    notDetected = []
    positions = {}
    for sym in cfg['targets']:
        tradedSym = findAFBITradedSym(sym)
        if tradedSym in dfPositions['BB Yellow Key'].values:
            row = np.where(dfPositions['BB Yellow Key'] == tradedSym)[0][0]
            positions[sym] = int(dfPositions.iloc[row]['Notional Quantity'])
        else:
            notDetected.append(sym)
            positions[sym] = 0

    if len(notDetected) != 0:
        lg.info(f"No AFBI Positions Detected For {notDetected}, Initialising At 0.")
    return positions


def findEmailTime(filename):
    for s in ['CBCT EOD POSITIONS_', '.xls']:
        filename = filename.replace(s, '')
    return pd.Timestamp(datetime.datetime.strptime(filename, '%m_%d_%Y_%H_%M_%S'))


def pullAFBIPositions(gmailService):
    latestEmail = gmail.pullLatestPosFile(gmailService, searchQuery="CBCT EOD POSITIONS",
                                          fileQuery="CBCT EOD POSITIONS")
    lastPosTime = findEmailTime(latestEmail['filename'])
    utility.logPositionDelay(lastPosTime, timezone, investor='AFBI')
    return latestEmail['data']


def findAFBITradedSym(sym):
    refData = utility.loadRefData()
    return refData.loc[refData['iqfUnadjusted'] == sym]['afbiTradedSym'].values[0]


def createAFBITradeCSV(cfg, fitModels, trades, execMd):
    afbiAccount = "CBCTBULK"
    orderType = "LMT"
    limitPrices = common.findLimitPrices(cfg, execMd, trades)
    cancelTime = common.createCancelTime(execMd)
    stopPrice = ""
    tif = "DAY"
    broker = "MSET"
    cols = ['Account', 'BB Yellow Key', 'Order Type', 'Side', 'Amount', 'Limit', 'Stop Price', 'TIF', 'Broker',
            "refPrice", f'refTime', 'Cancel Time', 'Current Position', 'Target Position', 'Description',
            'Exchange', 'maxPosition', 'maxTradeSize']
    out = []
    for sym in trades:
        tradedSym = utility.findIqfTradedSym(sym)
        bbSym = findAFBITradedSym(sym)
        qty = trades[sym]
        side = common.findSide(qty)
        limitPrice = limitPrices[sym]
        refPrice = common.findRefPrice(execMd, sym)
        lastTime = execMd[f'{tradedSym}_lastTS']
        initPos = fitModels[sym].initHoldings
        targetPos = fitModels[sym].initHoldings + trades[sym]
        desc = utility.findDescription(sym)
        exchange = utility.findExchange(sym)
        maxPos = fitModels[sym].maxPosition
        maxTradeSize = fitModels[sym].maxTradeSize
        symTrade = [afbiAccount, bbSym, orderType, side, qty, limitPrice, stopPrice, tif, broker, refPrice, lastTime,
                    cancelTime, initPos, targetPos, desc, exchange, maxPos, maxTradeSize]
        out.append(symTrade)

    return pd.DataFrame(out, columns=cols).set_index('Account')


def sendAFBITradeEmail(tradesPath, timeSig):
    sendFrom = "positions.afbi.cbct@sydneyquantitative.com"
    sendTo = ["ann.finaly@afbilp.com", "cem.ulu@afbillc.com"]
    sendCC = ["matthew.ramanah@sydneyquantitative.com", "bill.passias@afbillc.com", "christian.beulen@afbilp.com"]
    username = sendFrom
    password = "SydQuantPos23"
    subject = "CBCT tradeFile"
    message = f"CBCT_{timeSig}"
    filename = f"CBCT_{timeSig}.csv"

    gmail.sendFile(tradesPath, sendFrom, sendTo, sendCC, username, password, subject, message, filename)
    lg.info("Sent AFBI TradeFile")
    return


def sendAFBITradeFile(cfg, trades, fitModels, execMd):
    if isDeskManned():
        tradeCSV = createAFBITradeCSV(cfg, fitModels, trades, execMd)
        tradesPath = common.saveTradeLogs(tradeCSV, execMd['timeSig'], investor='AFBI')
        sendAFBITradeEmail(tradesPath, execMd['timeSig'])

    return
