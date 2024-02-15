from pyConfig import *
from modules import utility, gmail

timezone = 'US/Eastern'

unmannedHours = {
    "Monday": ("04:00", "08:00"),
    "Tuesday": ("04:00", "08:00"),
    "Wednesday": ("04:00", "08:00"),
    "Thursday": ("04:00", "08:00"),
    "Friday": ("04:00", "08:00"),
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


def detectAFBIPositions(cfg):
    dfPositions = pullAFBIPositions()
    notDetected = []
    positions = {}
    for sym in cfg['targets']:
        tradedSym = utility.findTradedSym(sym)
        if tradedSym in dfPositions['BB Yellow Key'].values:
            row = np.where(dfPositions['BB Yellow Key'] == tradedSym)[0][0]
            positions[sym] = int(dfPositions.iloc[row]['Notional Quantity'])
        else:
            notDetected.append(sym)
            positions[sym] = 0

    if len(notDetected) != 0:
        lg.info(f"Can't find positions from AFBI for {notDetected}, initialising at 0 for now.")
    return positions


def findEmailTime(filename):
    for s in ['CBCT EOD POSITIONS_', '.xls']:
        filename = filename.replace(s, '')
    return pd.Timestamp(datetime.datetime.strptime(filename, '%m_%d_%Y_%H_%M_%S'))


def pullAFBIPositions():
    afbiCredentials = interfaceRoot + "credentials.json"
    afbiToken = interfaceRoot + "token.json"
    afbiEmailRegex = "CBCT EOD POSITIONS"

    service = gmail.get_gmail_service(afbiCredentials, afbiToken)
    latestEmail = gmail.pullLatestPosFile(service, afbiEmailRegex)
    lastPosTime = findEmailTime(latestEmail['filename'])
    utility.logPositionDelay(lastPosTime, timezone)
    return latestEmail['data']


def findSide(qty):
    if qty < 0:
        return "S"
    elif qty > 0:
        return "B"
    else:
        return ""


def findTickSlipTol(cfg, sym):
    return int(pctSlipTol * cfg['fitParams']['basket']['aveTicksProfit'][sym])


def findLimitPrices(cfg, md, trades):
    limitPrices = {}
    for sym in trades:
        if trades[sym] == 0:
            limitPrices[sym] = ""
        else:
            sign = np.sign(trades[sym])
            tCost = sign * 0.5 * utility.findEffSpread(sym)
            slippage = sign * findTickSlipTol(cfg, sym) * utility.findTickSize(sym)
            tradedSym = utility.findIqfTradedSym(sym)
            limitPrices[sym] = round(md[f'{tradedSym}_close'] + tCost + slippage, noDec)

            if sym in list(priceMultipliers.keys()):
                limitPrices[sym] = round(priceMultipliers[sym] * limitPrices[sym], noDec)

    return limitPrices


def createCancelTime(md):
    cancelAfter = pd.Timedelta(minutes=30)
    return pd.Timestamp(datetime.datetime.strptime(md['timeSig'], '%Y_%m_%d_%H')) + cancelAfter


def findRefPrice(md, sym):
    tradedSym = utility.findIqfTradedSym(sym)
    if sym in list(priceMultipliers.keys()):
        return round(priceMultipliers[sym] * md[f'{tradedSym}_close'], noDec)
    return md[f'{tradedSym}_close']


def createTradeCSV(cfg, fitModels, trades, md, initPositions):
    afbiAccount = "CBCTBULK"
    orderType = "LMT"
    limitPrices = findLimitPrices(cfg, md, trades)
    cancelTime = createCancelTime(md)
    stopPrice = ""
    tif = "DAY"
    broker = "SGXE"
    cols = ['Account', 'BB Yellow Key', 'Order Type', 'Side', 'Amount', 'Limit', 'Stop Price', 'TIF', 'Broker',
            "refPrice", f'refTime', 'Cancel Time', 'Current Position', 'Target Position', 'Description',
            'Exchange', 'maxPosition', 'maxTradeSize']
    out = []
    for sym in trades:
        bbSym = utility.findTradedSym(sym)
        qty = trades[sym]
        side = findSide(qty)
        limitPrice = limitPrices[sym]
        refPrice = findRefPrice(md, sym)
        lastTime = md[f'{sym}_lastTS']
        initPos = initPositions[sym]
        targetPos = initPositions[sym] + trades[sym]
        desc = utility.findDescription(sym)
        exchange = utility.findExchange(sym)
        maxPos = fitModels[sym].maxPosition
        liquidityCap = fitModels[sym].liquidityCap
        symTrade = [afbiAccount, bbSym, orderType, side, qty, limitPrice, stopPrice, tif, broker, refPrice, lastTime,
                    cancelTime, initPos, targetPos, desc, exchange, maxPos, liquidityCap]
        out.append(symTrade)

    return pd.DataFrame(out, columns=cols).set_index('Account')


def findNotionalExposure(fitModels, sym, targetPos):
    raw = fitModels[sym].notionalPerLot * targetPos
    if np.sign(raw) < 0:
        return '-${:,}'.format(abs(raw))
    return '${:,}'.format(raw)


def createSummaryCSV(cfg, fitModels, trades, md, initPositions):
    limitPrices = findLimitPrices(cfg, md, trades)
    cols = ['Description', 'notionalExposure', 'normedPos', 'liq', 'currentPos', 'targetPos', 'maxPos', 'maxTradeSize',
            'notionalPerLot', 'tradeSide', 'tradeQty', 'limitPrice', "refPrice", f'refTime', 'BB Yellow Key',
            'Exchange', 'contractChange']
    out = []
    for sym in trades:
        desc = utility.findDescription(sym)
        bbSym = utility.findTradedSym(sym)
        qty = trades[sym]
        side = findSide(qty)
        limitPrice = limitPrices[sym]
        lastPrice = md[f'{sym}_close']
        lastTime = md[f'{sym}_lastTS']
        initPos = initPositions[sym]
        targetPos = initPositions[sym] + trades[sym]
        exchange = utility.findExchange(sym)
        maxPos = fitModels[sym].maxPosition
        liquidityCap = fitModels[sym].liquidityCap
        liquidity = int(fitModels[sym].target.liquidity)
        normedHoldings = round(fitModels[sym].normedHoldings, 3)
        notionalPerLot = '${:,}'.format(fitModels[sym].notionalPerLot)
        notionalExposure = findNotionalExposure(fitModels, sym, targetPos)
        contractChange = fitModels[sym].target.contractChange
        symTrade = [desc, notionalExposure, normedHoldings, liquidity, initPos, targetPos, maxPos, liquidityCap,
                    notionalPerLot, side, qty, limitPrice, lastPrice, lastTime, bbSym, exchange, contractChange]
        out.append(symTrade)

    return pd.DataFrame(out, columns=cols).set_index('Description')


def detectRiskLimits(cfg):
    dfLimits = pd.read_csv(riskPath)
    riskLimits = {}
    for sym in cfg['targets']:
        tradedSym = utility.findTradedSym(sym)
        row = np.where(dfLimits['Bloom Ticker'] == tradedSym)[0][0]
        riskLimits[sym] = {"maxPosition": int(dfLimits.iloc[row]['maxPosition']),
                           "maxTradeSize": int(dfLimits.iloc[row]['maxTradeSize'])}
    return riskLimits


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
