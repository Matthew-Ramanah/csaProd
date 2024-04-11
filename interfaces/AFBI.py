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
    for sym in utility.findProdSyms():
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


def createAFBITradeCSV(cfg, fitModels, trades, execMD, md, initPositions):
    afbiAccount = "CBCTBULK"
    orderType = "MKT"
    algoType = "TWAP"
    cancelTime = common.createCancelTime(execMD)
    stopPrice = ""
    limitPrice = ""
    tif = "DAY"
    broker = "MSET"
    cols = ['Account', 'BB Yellow Key', 'Order Type', 'Side', 'Amount', 'Limit', 'Stop Price', 'TIF', 'Broker', "Algo",
            "refPrice", f'refTime', 'Cancel Time', 'Current Position', 'Target Position', 'Description',
            'Exchange', 'maxPosition', 'maxTradeSize']
    out = []
    prodSyms = utility.findProdSyms()
    for sym in prodSyms:
        tradedSym = utility.findIqfTradedSym(sym)
        bbSym = findAFBITradedSym(sym)
        refPrice = common.findRefPrice(execMD, sym)
        lastTime = execMD[f'{tradedSym}_lastTS']
        desc = utility.findDescription(sym)
        exchange = utility.findExchange(sym)
        initPos = initPositions[sym]
        if sym in trades:
            maxPos = fitModels[sym].maxPosition
            maxTradeSize = fitModels[sym].maxTradeSize
            qty = trades[sym]
            side = common.findSide(qty)
            targetPos = fitModels[sym].initHoldings + trades[sym]
        else:
            maxPos = utility.dummyMaxPosition(cfg, sym, md)
            maxTradeSize = np.ceil(maxPos * maxAssetDelta).astype(int)
            qty = utility.findMaxFlattenQty(initPos, maxTradeSize)
            side = common.findSide(qty)
            targetPos = initPos + qty

        symTrade = [afbiAccount, bbSym, orderType, side, qty, limitPrice, stopPrice, tif, broker, algoType, refPrice,
                    lastTime, cancelTime, initPos, targetPos, desc, exchange, maxPos, maxTradeSize]
        out.append(symTrade)

    return pd.DataFrame(out, columns=cols).set_index('Account')


def sendAFBITradeEmail(tradesPath, timeSig):
    sendFrom = "positions.afbi.cbct@sydneyquantitative.com"
    sendTo = ["matthew.ramanah@sydneyquantitative.com"]  # ["ann.finaly@afbilp.com", "cem.ulu@afbillc.com"]
    sendCC = []  # ["matthew.ramanah@sydneyquantitative.com", "bill.passias@afbillc.com", "christian.beulen@afbilp.com"]
    username = sendFrom
    password = "SydQuantPos23"
    subject = "CBCT tradeFile"
    message = f"CBCT_{timeSig}"
    filename = f"CBCT_{timeSig}.csv"

    gmail.sendFile(tradesPath, sendFrom, sendTo, sendCC, username, password, subject, message, filename)
    lg.info("Sent AFBI TradeFile")
    return


def sendAFBITradeFile(cfg, trades, fitModels, execMD, md, initPositions):
    tradeCSV = createAFBITradeCSV(cfg, fitModels, trades, execMD, md, initPositions)
    print(tradeCSV)
    if False:#isDeskManned():
        tradesPath = common.saveTradeLogs(tradeCSV, execMD['timeSig'], investor='AFBI')
        sendAFBITradeEmail(tradesPath, execMD['timeSig'])

    return
