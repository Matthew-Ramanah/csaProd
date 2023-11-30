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


def findSide(qty):
    if qty < 0:
        return "S"
    elif qty > 0:
        return "B"
    else:
        return ""


def createTradeCSV(trades, md, initPositions, timeSig):
    refData = utility.loadRefData()
    afbiAccount = "CBCT"
    orderType = "MKT"
    limitPrice = ""
    stopPrice = ""
    tif = "DAY"
    broker = "MSET"
    cols = ['Account', 'BB Yellow Key', 'Order Type', 'Side', 'Amount', 'Limit', 'Stop Price', 'TIF', 'Broker',
            "Last Price", 'Last Time', 'Current Position', 'Target Position', 'Description']
    out = []
    for sym in trades:
        bbSym = f"{md[f'{sym}_symbol']} {refData.loc[sym]['assetClass']}"
        qty = trades[sym]
        side = findSide(qty)
        lastPrice = md[f'{sym}_midPrice']
        initPos = initPositions[sym]
        targetPos = initPositions[sym] + trades[sym]
        desc = refData.loc[sym]['description']
        symTrade = [afbiAccount, bbSym, orderType, side, qty, limitPrice, stopPrice, tif, broker, lastPrice, timeSig,
                    initPos, targetPos, desc]
        out.append(symTrade)

    return pd.DataFrame(out, columns=cols).set_index('Account')


def generateAFBITradeFile(fitModels, md, initPositions):
    timeSig = (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime('%Y_%m_%d_%H')
    tradesPath = f"{logRoot}CBCT_{timeSig}.csv"

    # Generate CSV & dict
    trades = utility.generateTrades(fitModels)
    tradeCSV = createTradeCSV(trades, md, initPositions, timeSig)
    print(tradeCSV)

    # Save to Log & Email
    tradeCSV.to_csv(tradesPath)
    sendAFBITradeEmail(tradesPath, timeSig)
    return trades


def sendAFBITradeEmail(tradesPath, timeSig):
    sendFrom = "positions.afbi.cbct@sydneyquantitative.com"
    sendTo = "matthew.ramanah@sydneyquantitative.com"
    username = sendFrom
    password = "SydQuantPos23"
    subject = "CBCT tradeFile"
    message = f"CBCT_{timeSig}"
    filename = f"CBCT_{timeSig}"
    gmail.sendTradeFile(tradesPath, sendFrom, sendTo, username, password, subject, message, filename)

    return
