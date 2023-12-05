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
    afbiCredentials = interfaceRoot + "credentials.json"
    afbiToken = interfaceRoot + "token.json"
    afbiEmailRegex = "CBCT EOD POSITIONS"

    service = gmail.get_gmail_service(afbiCredentials, afbiToken)
    latestEmail = gmail.pullLatestPosFile(service, afbiEmailRegex)
    lg.info('Latest AFBI Position File: ' + latestEmail['filename'])
    return latestEmail['data']


def findSide(qty):
    if qty < 0:
        return "S"
    elif qty > 0:
        return "B"
    else:
        return ""


def createTradeCSV(trades, md, initPositions, timezone):
    refData = utility.loadRefData()
    afbiAccount = "CBCT"
    orderType = "MKT"
    limitPrice = ""
    stopPrice = ""
    tif = "DAY"
    broker = "MSET"
    cols = ['Account', 'BB Yellow Key', 'Order Type', 'Side', 'Amount', 'Limit', 'Stop Price', 'TIF', 'Broker',
            "refPrice", f'refTime: {timezone}', 'Current Position', 'Target Position', 'Description', 'Exchange']
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
        symTrade = [afbiAccount, bbSym, orderType, side, qty, limitPrice, stopPrice, tif, broker, lastPrice, lastTime,
                    initPos, targetPos, desc, exchange]
        out.append(symTrade)

    return pd.DataFrame(out, columns=cols).set_index('Account')


def generateAFBITradeFile(fitModels, md, initPositions, timeSig, timezone):
    tradesPath = f"{logRoot}CBCT_{timeSig}.csv"

    # Generate CSV & dict
    trades = utility.generateTrades(fitModels)
    tradeCSV = createTradeCSV(trades, md, initPositions, timezone)
    print(tradeCSV)

    # Save to Log & Email
    tradeCSV.to_csv(tradesPath)
    sendAFBITradeEmail(tradesPath, timeSig)
    return trades


def sendAFBITradeEmail(tradesPath, timeSig):
    sendFrom = "positions.afbi.cbct@sydneyquantitative.com"
    sendTo = sendFrom
    username = sendFrom
    password = "SydQuantPos23"
    subject = "CBCT tradeFile"
    message = f"CBCT_{timeSig}"
    filename = f"CBCT_{timeSig}.csv"
    gmail.sendTradeFile(tradesPath, sendFrom, sendTo, username, password, subject, message, filename)

    return
