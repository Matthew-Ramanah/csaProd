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
    for sym in utility.findProdSyms():
        qubeInternal = findQubeInternal(sym)
        if qubeInternal in dfPositions['Instrument'].values:
            row = np.where(dfPositions['Instrument'] == qubeInternal)[0][0]
            positions[sym] = int(dfPositions.iloc[row]['Position EOD USD'])
        else:
            notDetected.append(sym)
            positions[sym] = 0

    if len(notDetected) != 0:
        lg.info(f"No Qube Positions Detected For {notDetected}, Initialising At 0.")
    return positions


def pullQubePositions(gmailService):
    latestEmail = gmail.pullLatestPosFile(gmailService, searchQuery="QQSec", fileQuery="QQSec_Detailed_CB")
    lastPosTime = findEmailTime(latestEmail['filename'])
    utility.logPositionDelay(lastPosTime, timezone, investor='Qube')
    return latestEmail['data']


def findEmailTime(filename):
    for s in ['QQSec_Detailed_CB_', '.xlsx']:
        filename = filename.replace(s, '')
    return pd.Timestamp(filename)


def findQubeRIC(sym):
    refData = utility.loadRefData()
    return refData.loc[refData['iqfUnadjusted'] == sym]['QubeRIC'].values[0]


def findQubeInternal(sym):
    refData = utility.loadRefData()
    return refData.loc[refData['iqfUnadjusted'] == sym]['QubeInternal'].values[0]


def sendQubeTradeFile(cfg, trades, fitModels, execMd, md, initPositions):
    if isDeskManned():
        tradeCSV = createQubeTradeCSV(cfg, fitModels, trades, execMd, md, initPositions)
        tradesPath = common.saveTradeLogs(tradeCSV, execMd['timeSig'], investor='Qube')
        sendQubeTradeEmail(tradesPath, execMd['timeSig'])

    return


def findExtraKey(strategy, internal_code):
    return f'{strategy}_{internal_code}'


def findQubeCurrency(sym):
    refData = utility.loadRefData()
    return refData.loc[refData['iqfUnadjusted'] == sym]['notionalCurrency'].values[0]


def findQubeTargetNotional(fitModels, sym, hysteresis=0.05):
    raw = fitModels[sym].nativeTargetNotional
    return round((1 + hysteresis) * raw, 2)


def createValueTS(timezone='UTC'):
    return datetime.datetime.now(pytz.timezone(timezone)).strftime('%Y/%m/%d %H:%M')


def createQubeTradeCSV(cfg, fitModels, trades, execMd, md, initPositions):
    id_specific = "CB"
    value_ts = createValueTS()
    strategy = 'S1'
    advisor_name = "Christian BEULEN"
    cols = ['id_specific', 'extra_key', 'value_ts', 'strategy', 'internal_code', 'ric', 'ticker', 'target_notional',
            'currency', "target_contracts", f'ref_price', 'advisor_name', 'desc', 'initPos', 'maxPos', 'maxTradeSize']
    out = []
    prodSyms = utility.findProdSyms()
    for sym in prodSyms:
        internal_code = findQubeInternal(sym)
        extra_key = findExtraKey(strategy, internal_code)
        ric = findQubeRIC(sym)
        ticker = ric
        desc = utility.findDescription(sym)
        currency = findQubeCurrency(sym)
        ref_price = common.findRefPrice(execMd, sym)

        if sym in trades:
            initPos = fitModels[sym].initHoldings
            maxPos = fitModels[sym].maxPosition
            maxTradeSize = fitModels[sym].maxTradeSize
            target_notional = findQubeTargetNotional(fitModels, sym)
            target_contracts = fitModels[sym].initHoldings + trades[sym]
        else:
            maxPos = utility.dummyMaxPosition(cfg, sym, md)
            maxTradeSize = np.ceil(maxPos * maxAssetDelta).astype(int)
            target_contracts = 0
            target_notional = 0
            initPos = inferQubePosition(initPositions[sym], sym, md)

        symTrade = [id_specific, extra_key, value_ts, strategy, internal_code, ric, ticker, target_notional, currency,
                    target_contracts, ref_price, advisor_name, desc, initPos, maxPos, maxTradeSize]
        out.append(symTrade)

    return pd.DataFrame(out, columns=cols).set_index('id_specific')


def inferQubePosition(initPos, sym, md):
    notionalPerLot = utility.calcNotionalPerLot(sym, md)
    return int(initPos / notionalPerLot)


def sendQubeTradeEmail(tradesPath, timeSig):
    sendFrom = "positions.afbi.cbct@sydneyquantitative.com"
    sendTo = ["matthew.ramanah@sydneyquantitative.com"]  # ,"christian.beulen@sydneyquantitative.com"]
    sendCC = []
    username = sendFrom
    password = "SydQuantPos23"
    subject = "Qube tradeFile"
    message = f"Qube_{timeSig}"
    filename = f"Qube_{timeSig}.csv"

    gmail.sendFile(tradesPath, sendFrom, sendTo, sendCC, username, password, subject, message, filename)
    lg.info("Sent Qube TradeFile")
    return
