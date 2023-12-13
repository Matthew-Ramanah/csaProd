from pyConfig import *
from modules import utility, gmail

timezone = 'US/Eastern'

unmannedHours = {
    "Monday": ("04:00", "08:00"),
    "Tuesday": ("04:00", "08:00"),
    "Wednesday": ("04:00", "08:00"),
    "Thursday": ("04:00", "08:00"),
    "Friday": ("04:00", "08:00"),
    "Saturday": ("04:00", "23:59"),
    "Sunday": ("00:00", "18:59")
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
    refData = utility.loadRefData()
    dfPositions = pullAFBIPositions()
    notDetected = []
    positions = {}
    for sym in cfg['targets']:
        tradedSym = refData.loc[sym]['tradedSym']
        if tradedSym in dfPositions['BB Yellow Key'].values:
            row = np.where(dfPositions['BB Yellow Key'] == tradedSym)[0][0]
            if dfPositions.iloc[row]['Active']:
                positions[sym] = int(dfPositions.iloc[row]['Notional Quantity'])
            else:
                # We really don't want this to happen, have the system exit if it detects a bad contract.
                raise ValueError(f'{sym}: Trying to trade an inactive contract. Update refData.')
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


def createTradeCSV(fitModels, trades, md, initPositions, timezone):
    refData = utility.loadRefData()
    afbiAccount = "CBCTBULK"
    orderType = "MKT"
    limitPrice = ""
    stopPrice = ""
    tif = "DAY"
    broker = "MSET"
    cols = ['Account', 'BB Yellow Key', 'Order Type', 'Side', 'Amount', 'Limit', 'Stop Price', 'TIF', 'Broker',
            "refPrice", f'refTime: {timezone}', 'Current Position', 'Target Position', 'Description', 'Exchange',
            'maxPosition', 'maxTradeSize']
    out = []
    for sym in trades:
        bbSym = refData.loc[sym]['tradedSym']
        qty = trades[sym]
        side = findSide(qty)
        lastPrice = md[f'{sym}_midPrice']
        lastTime = md[f'{sym}_lastTS']
        initPos = initPositions[sym]
        targetPos = initPositions[sym] + trades[sym]
        desc = refData.loc[sym]['description']
        exchange = refData.loc[sym]['exchange']
        maxPos = fitModels[sym].maxPosition
        maxTradeSize = fitModels[sym].maxTradeSize
        symTrade = [afbiAccount, bbSym, orderType, side, qty, limitPrice, stopPrice, tif, broker, lastPrice, lastTime,
                    initPos, targetPos, desc, exchange, maxPos, maxTradeSize]
        out.append(symTrade)

    return pd.DataFrame(out, columns=cols).set_index('Account')


def generateAFBITradeFile(fitModels, md, initPositions, timezone, send=True):
    tradesPath = f"{logRoot}trades/CBCT_{md['timeSig']}.csv"

    # Generate CSV & dict
    trades = utility.generateTrades(fitModels)
    tradeCSV = createTradeCSV(fitModels, trades, md, initPositions, timezone)
    print(tradeCSV)

    # Save to Log & Email
    tradeCSV.to_csv(tradesPath)

    if send:
        if isDeskManned():
            sendAFBITradeEmail(tradesPath, md['timeSig'])
        else:
            lg.info("Not sending email as desk is unmanned.")
    return trades


def sendAFBITradeEmail(tradesPath, timeSig):
    sendFrom = "positions.afbi.cbct@sydneyquantitative.com"
    sendTo = ["ann.finaly@afbilp.com", "cem.ulu@afbillc.com"]
    sendCC = ["stephen.klein@afbillc.com", "bill.passias@afbillc.com", "christian.beulen@afbilp.com",
              "matthew.ramanah@sydneyquantitative.com"]
    username = sendFrom
    password = "SydQuantPos23"
    subject = "CBCT tradeFile"
    message = f"CBCT_{timeSig}"
    filename = f"CBCT_{timeSig}.csv"
    gmail.sendTradeFile(tradesPath, sendFrom, sendTo, sendCC, username, password, subject, message, filename)

    return


def detectRiskLimits(cfg):
    riskPath = f"{root}models/AFBI/config/riskLimits.csv"
    dfLimits = pd.read_csv(riskPath)
    refData = utility.loadRefData()
    riskLimits = {}
    for sym in cfg['targets']:
        tradedSym = refData.loc[sym]['tradedSym']
        row = np.where(dfLimits['Bloom Ticker'] == tradedSym)[0][0]
        riskLimits[sym] = {"maxPosition": int(dfLimits.iloc[row]['maxPosition']),
                           "maxTradeSize": int(dfLimits.iloc[row]['maxTradeSize'])}
    return riskLimits
