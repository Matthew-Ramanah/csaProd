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


def findLimitPrices(cfg, md, trades):
    limitPrices = {}
    for sym in trades:
        if trades[sym] == 0:
            limitPrices[sym] = ""
        else:
            sign = np.sign(trades[sym])
            tCost = sign * utility.findEffSpread(sym)
            slippage = sign * common.findTickSlipTol(cfg, sym) * utility.findTickSize(sym)
            tradedSym = utility.findIqfTradedSym(sym)
            limitPrices[sym] = round(md[f'{tradedSym}_close'] + tCost + slippage, noDec)

            if sym in list(priceMultipliers.keys()):
                limitPrices[sym] = round(priceMultipliers[sym] * limitPrices[sym], noDec)

    return limitPrices


def findAFBITradedSym(sym):
    refData = utility.loadRefData()
    return refData.loc[refData['iqfUnadjusted'] == sym]['afbiTradedSym'].values[0]


def createTradeCSV(cfg, fitModels, trades, execMd, initPositions):
    afbiAccount = "CBCTBULK"
    orderType = "LMT"
    limitPrices = findLimitPrices(cfg, execMd, trades)
    cancelTime = common.createCancelTime(execMd)
    stopPrice = ""
    tif = "DAY"
    broker = "SGXE"
    cols = ['Account', 'BB Yellow Key', 'Order Type', 'Side', 'Amount', 'Limit', 'Stop Price', 'TIF', 'Broker',
            "refPrice", f'refTime', 'Cancel Time', 'Current Position', 'Target Position', 'Description',
            'Exchange', 'maxPosition', 'maxTradeSize']
    out = []
    for sym in trades:
        bbSym = findAFBITradedSym(sym)
        qty = trades[sym]
        side = common.findSide(qty)
        limitPrice = limitPrices[sym]
        refPrice = common.findRefPrice(execMd, sym)
        lastTime = execMd[f'{sym}_lastTS']
        initPos = initPositions[sym]
        targetPos = initPositions[sym] + trades[sym]
        desc = utility.findDescription(sym)
        exchange = utility.findExchange(sym)
        maxPos = fitModels[sym].maxPosition
        maxTradeSize = fitModels[sym].maxTradeSize
        symTrade = [afbiAccount, bbSym, orderType, side, qty, limitPrice, stopPrice, tif, broker, refPrice, lastTime,
                    cancelTime, initPos, targetPos, desc, exchange, maxPos, maxTradeSize]
        out.append(symTrade)

    return pd.DataFrame(out, columns=cols).set_index('Account')


def createSummaryCSV(cfg, fitModels, trades, md, initPositions):
    limitPrices = findLimitPrices(cfg, md, trades)
    cols = ['Description', 'targetNotional', 'normedPos', 'liq', 'currentPos', 'targetPos', 'maxPos', 'maxTradeSize',
            'notionalPerLot', 'tradeSide', 'tradeQty', 'limitPrice', "refPrice", f'refTime', 'BB Yellow Key',
            'Exchange']
    out = []
    for sym in trades:
        desc = utility.findDescription(sym)
        bbSym = utility.findBBTradedSym(sym)
        qty = trades[sym]
        side = common.findSide(qty)
        limitPrice = limitPrices[sym]
        refPrice = common.findRefPrice(md, sym)
        lastTime = md[f'{sym}_lastTS']
        initPos = initPositions[sym]
        targetPos = initPositions[sym] + trades[sym]
        exchange = utility.findExchange(sym)
        maxPos = fitModels[sym].maxPosition
        maxTradeSize = fitModels[sym].maxTradeSize
        liquidity = int(fitModels[sym].target.liquidity)
        normedHoldings = round(fitModels[sym].normedHoldings, 3)
        notionalPerLot = '${:,}'.format(fitModels[sym].notionalPerLot)
        targetNotional = common.findTargetExposure(fitModels, sym, targetPos)
        symTrade = [desc, targetNotional, normedHoldings, liquidity, initPos, targetPos, maxPos, maxTradeSize,
                    notionalPerLot, side, qty, limitPrice, refPrice, lastTime, bbSym, exchange]
        out.append(symTrade)

    return pd.DataFrame(out, columns=cols).set_index('Description')


def sendAFBITradeEmail(tradesPath, timeSig):
    lg.info("Sending tradeFile")
    sendFrom = "positions.afbi.cbct@sydneyquantitative.com"
    sendTo = ["ann.finaly@afbilp.com", "cem.ulu@afbillc.com"]
    sendCC = ["matthew.ramanah@sydneyquantitative.com", "bill.passias@afbillc.com", "christian.beulen@afbilp.com"]
    username = sendFrom
    password = "SydQuantPos23"
    subject = "CBCT tradeFile"
    message = f"CBCT_{timeSig}"
    filename = f"CBCT_{timeSig}.csv"

    gmail.sendFile(tradesPath, sendFrom, sendTo, sendCC, username, password, subject, message, filename)

    return


def sendAFBITradeFile(cfg, trades, fitModels, execMd, initPositions):
    # Generate CSV & dict
    tradeCSV = createTradeCSV(cfg, fitModels, trades, execMd, initPositions)

    # Save to Log & Email
    tradesPath = saveAFBILogs(tradeCSV, execMd['timeSig'])
    if isDeskManned():
        sendAFBITradeEmail(tradesPath, execMd['timeSig'])
    else:
        lg.info("Not sending tradeFile as desk is unmanned.")

    return trades


def saveAFBILogs(tradeCSV, timeSig):
    os.makedirs(f"{logRoot}trades/", exist_ok=True)
    tradesPath = f"{logRoot}trades/CBCT_{timeSig}.csv"
    tradeCSV.to_csv(tradesPath)
    return tradesPath


def saveAFBISummary(summaryCSV, timeSig):
    os.makedirs(f"{logRoot}summary/", exist_ok=True)
    sumPath = f"{logRoot}summary/CBCT_{timeSig}.csv"
    summaryCSV.to_csv(sumPath)
    return sumPath
