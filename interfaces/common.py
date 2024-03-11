from pyConfig import *
from modules import utility, gmail, models
from interfaces import AFBI, Qube


def detectConfigs(cfgFiles):
    cfgs = {}
    for file in cfgFiles:
        with open(f"{root}config/{file}.json", 'r') as f:
            cfg = json.load(f)
        cfgs[cfg['investor']] = cfg
    return cfgs


def initialiseSystems(cfgs):
    initSeeds, initPositions, fitModels = {}, {}, {}
    for investor in cfgs:
        initSeeds[investor] = utility.loadInitSeeds(cfgs[investor])
        initPositions[investor] = detectPositions(cfgs[investor])
        fitModels[investor] = initialiseModels(cfgs[investor], seeds=initSeeds[investor],
                                               positions=initPositions[investor], prod=True)
    return initSeeds, initPositions, fitModels


def detectPositions(cfg):
    creds = f"{interfaceRoot}credentials/credentials.json"
    token = f"{interfaceRoot}credentials/token.json"
    gmailService = gmail.get_gmail_service(creds, token)

    if cfg["investor"] == "AFBI":
        initPositions = AFBI.detectAFBIPositions(cfg, gmailService)
    elif cfg['investor'] == 'Qube':
        initPositions = Qube.detectQubePositions(cfg, gmailService)
    else:
        raise ValueError("Unknown Investor")
    return initPositions


def findRefPrice(md, sym):
    tradedSym = utility.findIqfTradedSym(sym)
    if sym in list(priceMultipliers.keys()):
        return round(priceMultipliers[sym] * md[f'{tradedSym}_close'], noDec)
    return md[f'{tradedSym}_close']


def sendTradeFiles(cfgs, initPositions, trades, fitModels, execMD):
    for investor in cfgs:
        if investor == "AFBI":
            AFBI.sendAFBITradeFile(cfgs[investor], trades[investor], fitModels[investor], execMD,
                                   initPositions[investor])
        elif investor == "Qube":
            Qube.sendQubeTradeFile(trades[investor], fitModels[investor], execMD, initPositions[investor])
        else:
            raise ValueError("Unknown Investor")
    return


def findTargetExposure(fitModels, sym, targetPos):
    raw = fitModels[sym].notionalPerLot * targetPos
    if np.sign(raw) < 0:
        return '-${:,}'.format(abs(raw))
    return '${:,}'.format(raw)


def createCancelTime(md, cancelMinutes=30):
    cancelAfter = pd.Timedelta(minutes=cancelMinutes)
    return pd.Timestamp(datetime.datetime.strptime(md['timeSig'], '%Y_%m_%d_%H')) + cancelAfter


def findSide(qty):
    if qty < 0:
        return "S"
    elif qty > 0:
        return "B"
    else:
        return ""


def findTickSlipTol(cfg, sym):
    return int(pctSlipTol * cfg['fitParams']['basket']['aveTicksProfit'][sym])


def initialiseModels(cfg, seeds, positions, prod=False):
    fitModels = {}
    for sym in cfg['targets']:
        fitModels[sym] = models.assetModel(targetSym=sym, cfg=cfg, params=cfg['fitParams'][sym], seeds=seeds,
                                           initHoldings=positions[sym],
                                           riskLimits=cfg['fitParams']['basket']['riskLimits'], prod=prod)
    return fitModels


def updateModels(fitModels, md):
    for investor in fitModels:
        for sym in fitModels[investor]:
            fitModels[investor][sym].mdUpdate(md)
    return fitModels


def generateOutputFiles(cfgs, fitModels, mdPipe, initPositions, initSeeds, md, send, save):
    # Identify Trades
    trades = utility.detectTrades(fitModels)

    # Pull market data for execSyms
    execMD = mdPipe.pullExecMD()

    # Send tradeFiles & summary
    if send:
        sendTradeFiles(cfgs, initPositions, trades, fitModels, execMD)
        sendSummaryEmail()

    # Save Models
    if save:
        saveStates(cfgs, initSeeds, initPositions, md, trades, fitModels)

    return


def saveStates(cfgs, initSeeds, initPositions, md, trades, fitModels):
    for investor in cfgs:
        modelState = {
            "initSeeds": initSeeds[investor],
            "initPositions": initPositions[investor],
            "trades": trades[investor],
            "seedDump": {},
            "logs": {},
            "alphasLog": {}
        }

        for sym in fitModels[investor]:
            modelState['seedDump'][sym] = fitModels[investor][sym].seedDump
            modelState['logs'][sym] = fitModels[investor][sym].log[-1]
            modelState['alphasLog'][sym] = fitModels[investor][sym].alphasLog

        with open(f"{interfaceRoot}{investor}/modelState.json", 'w') as f:
            json.dump(modelState, f)
        lg.info("Saved Model State.")

        os.makedirs(f"{logRoot}{investor}/models/", exist_ok=True)
        with open(f"{logRoot}{investor}/models/{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["logs"], f)

        os.makedirs(f"{logRoot}{investor}/alphas/", exist_ok=True)
        with open(f"{logRoot}{investor}/alphas/{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["alphasLog"], f)
        lg.info("Saved Logs.")

        os.makedirs(f"{logRoot}{investor}/seeds/", exist_ok=True)
        with open(f"{logRoot}{investor}/seeds/{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["seedDump"], f)

    return


def saveSummaryCSV(sumCSV, timeSig, investor):
    os.makedirs(f"{logRoot}{investor}/summary/", exist_ok=True)
    sumPath = f"{logRoot}{investor}/summary/{timeSig}.csv"
    
    sumCSV.to_csv(sumPath)
    return sumPath

def createSummaryCSVs():
    return

def createSummaryCSV(cfgs, fitModels, trades, execMD, initPositions):
    cols = ['Description', 'usdTargetNotional', 'normedPos', 'liq', 'currentPos', 'targetPos', 'maxPos', 'maxTradeSize',
            'notionalPerLot', "refPrice", f'refTime', 'exchange', 'iqfTradedSym']
    out = []
    for sym in trades:
        desc = utility.findDescription(sym)
        qty = trades[sym]
        tradedSym = utility.findIqfTradedSym(sym)
        refPrice = findRefPrice(execMD, tradedSym)
        lastTime = execMD[f'{tradedSym}_lastTS']
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



def sendSummaryEmail(sumPaths, timeSig):

    sendFrom = "positions.afbi.cbct@sydneyquantitative.com"
    sendTo = ["matthew.ramanah@sydneyquantitative.com"]
    sendCC = []
    username = sendFrom
    password = "SydQuantPos23"
    subject = f"CSA Summary"
    message = f"{timeSig}"
    gmail.sendSummaryFiles(sumPaths, sendFrom, sendTo, sendCC, username, password, subject, message)
    return


def saveTradeLogs(tradeCSV, timeSig, investor):
    os.makedirs(f"{logRoot}{investor}/trades/", exist_ok=True)
    tradesPath = f"{logRoot}{investor}/trades/{timeSig}.csv"
    tradeCSV.to_csv(tradesPath)
    return tradesPath


def findLimitPrices(cfg, md, trades):
    limitPrices = {}
    for sym in trades:
        if trades[sym] == 0:
            limitPrices[sym] = ""
        else:
            sign = np.sign(trades[sym])
            tCost = sign * utility.findEffSpread(sym)
            slippage = sign * findTickSlipTol(cfg, sym) * utility.findTickSize(sym)
            tradedSym = utility.findIqfTradedSym(sym)
            limitPrices[sym] = round(md[f'{tradedSym}_close'] + tCost + slippage, noDec)

            if sym in list(priceMultipliers.keys()):
                limitPrices[sym] = round(priceMultipliers[sym] * limitPrices[sym], noDec)

    return limitPrices
