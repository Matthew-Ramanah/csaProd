from pyConfig import *
from modules import utility, gmail
from interfaces import common

timezone = 'US/Eastern'

unmannedHours = {
    "Monday": ("03:55", "07:55"),
    "Tuesday": ("03:55", "07:55"),
    "Wednesday": ("03:55", "07:55"),
    "Thursday": ("03:55", "07:55"),
    "Friday": ("03:55", "07:55"),
    "Saturday": ("00:00", "23:59"),
    "Sunday": ("00:00", "17:55")
}


def isDeskManned():
    """
    Note the dictionary specifies the times the desk is UNMANNED
    """
    localDT = datetime.datetime.now(pytz.timezone(timezone))
    localDay = dayOfWeekMap[localDT.weekday()]
    localTime = localDT.time()
    startTime = datetime.datetime.strptime(unmannedHours[localDay][0], '%H:%M').time()
    endTime = datetime.datetime.strptime(unmannedHours[localDay][1], '%H:%M').time()
    if localTime > startTime and localTime < endTime:
        return False
    else:
        return True


def detectAFBIPositions(cfg, gmailService):
    dfPositions = pullAFBIPositions(gmailService)
    notDetected = []
    positions = {}
    for sym in cfg['targets']:
        tradedSym = utility.findBBTradedSym(sym)
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
    latestEmail = gmail.pullLatestPosFile(gmailService, searchQuery="CBCT EOD POSITIONS")
    lastPosTime = findEmailTime(latestEmail['filename'])
    utility.logPositionDelay(lastPosTime, timezone)
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


def createTradeCSV(cfg, fitModels, trades, md, initPositions):
    afbiAccount = "CBCTBULK"
    orderType = "LMT"
    limitPrices = findLimitPrices(cfg, md, trades)
    cancelTime = common.createCancelTime(md)
    stopPrice = ""
    tif = "DAY"
    broker = "SGXE"
    cols = ['Account', 'BB Yellow Key', 'Order Type', 'Side', 'Amount', 'Limit', 'Stop Price', 'TIF', 'Broker',
            "refPrice", f'refTime', 'Cancel Time', 'Current Position', 'Target Position', 'Description',
            'Exchange', 'maxPosition', 'maxTradeSize']
    out = []
    for sym in trades:
        bbSym = utility.findBBTradedSym(sym)
        qty = trades[sym]
        side = common.findSide(qty)
        limitPrice = limitPrices[sym]
        refPrice = common.findRefPrice(md, sym)
        lastTime = md[f'{sym}_lastTS']
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


def sendAFBISummaryEmail(sumPath, timeSig):
    sendFrom = "positions.afbi.cbct@sydneyquantitative.com"
    sendTo = ["matthew.ramanah@sydneyquantitative.com"]
    sendCC = []
    username = sendFrom
    password = "SydQuantPos23"
    subject = "CBCT Summary"
    message = f"CBCT_{timeSig}"
    filename = f"CBCT_{timeSig}.csv"
    gmail.sendFile(sumPath, sendFrom, sendTo, sendCC, username, password, subject, message, filename)
    return


def generateAFBITradeFile(cfg, fitModels, md, initPositions, send=True, saveLogs=True):
    # Generate CSV & dict
    trades = utility.generateTrades(fitModels)
    tradeCSV = createTradeCSV(cfg, fitModels, trades, md, initPositions)
    sumCSV = createSummaryCSV(cfg, fitModels, trades, md, initPositions)
    print(sumCSV)

    # Save to Log & Email
    os.makedirs(f"{logRoot}trades/", exist_ok=True)
    tradesPath = f"{logRoot}trades/CBCT_{md['timeSig']}.csv"
    os.makedirs(f"{logRoot}summary/", exist_ok=True)
    sumPath = f"{logRoot}summary/CBCT_{md['timeSig']}.csv"
    if saveLogs:
        tradeCSV.to_csv(tradesPath)
        sumCSV.to_csv(sumPath)

        if send:
            if isDeskManned():
                sendAFBITradeEmail(tradesPath, md['timeSig'])
            else:
                lg.info("Not sending tradeFile as desk is unmanned.")
            sendAFBISummaryEmail(sumPath, md['timeSig'])

    return trades
