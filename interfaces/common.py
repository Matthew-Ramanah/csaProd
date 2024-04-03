from pyConfig import *
from modules import utility, gmail, models
from interfaces import AFBI, Qube

summaryTimes = [1, 7, 13, 19]


def detectConfigs(cfgFiles):
    cfgs = {}
    for file in cfgFiles:
        with open(f"{root}config/{file}.json", 'r') as f:
            cfg = json.load(f)
        cfgs[cfg['investor']] = cfg
    return cfgs


def deleteBadInits(cfgs, badInit):
    for x in badInit:
        del cfgs[x]
    return cfgs


def initialiseSystems(cfgs):
    initSeeds, initPositions, fitModels = {}, {}, {}
    badInit = []
    for investor in cfgs:
        try:
            initSeeds[investor] = utility.loadInitSeeds(cfgs[investor])
            initPositions[investor] = detectPositions(cfgs[investor])
            fitModels[investor] = initialiseModels(cfgs[investor], seeds=initSeeds[investor],
                                                   positions=initPositions[investor], prod=True)
        except:
            lg.info(f"Can't initialise {investor}, Removing from process.")
            badInit.append(investor)

    cfgs = deleteBadInits(cfgs, badInit)
    return initSeeds, initPositions, fitModels, cfgs


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


def sendTradeFiles(cfgs, trades, fitModels, execMD):
    for investor in cfgs:
        try:
            if investor == "AFBI":
                AFBI.sendAFBITradeFile(cfgs[investor], trades[investor], fitModels[investor], execMD)
            elif investor == "Qube":
                Qube.sendQubeTradeFile(trades[investor], fitModels[investor], execMD)
            else:
                raise ValueError("Unknown Investor")
        except:
            lg.info(f"Couldn't Send {investor} tradeFile.")
            continue
    return


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
        sendTradeFiles(cfgs, trades, fitModels, execMD)
        sendSummaryEmail(cfgs, fitModels, trades, execMD)

    # Save Models
    if save:
        saveStates(cfgs, initSeeds, initPositions, md, trades, fitModels)

    return trades, execMD


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

        os.makedirs(f"{interfaceRoot}states/", exist_ok=True)
        with open(f"{interfaceRoot}states/{investor}.json", 'w') as f:
            json.dump(modelState, f)

        os.makedirs(f"{logRoot}{investor}/models/", exist_ok=True)
        with open(f"{logRoot}{investor}/models/{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["logs"], f)

        os.makedirs(f"{logRoot}{investor}/alphas/", exist_ok=True)
        with open(f"{logRoot}{investor}/alphas/{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["alphasLog"], f)

        os.makedirs(f"{logRoot}{investor}/seeds/", exist_ok=True)
        with open(f"{logRoot}{investor}/seeds/{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["seedDump"], f)
    lg.info("Saved States.")
    return


def createSummaryCSVs(cfgs, fitModels, trades, execMD):
    sumCSVs = {}
    for investor in cfgs:
        sumCSVs[investor] = createSummaryCSV(fitModels[investor], trades[investor], execMD)
    return sumCSVs


def createSummaryCSV(fitModels, trades, execMD):
    cols = ['Description', 'usdTargetNotional', 'normedPos', 'liq', 'currentPos', 'targetPos', 'maxPos', 'maxTradeSize',
            'notionalPerLot', "refPrice", f'refTime', 'exchange', 'tradedSym']
    out = []
    for sym in trades:
        desc = utility.findDescription(sym)
        tradedSym = utility.findIqfTradedSym(sym)
        refPrice = execMD[f'{tradedSym}_close']
        refTime = execMD[f'{tradedSym}_lastTS']
        currentPos = fitModels[sym].initHoldings
        targetPos = fitModels[sym].initHoldings + trades[sym]
        exchange = utility.findExchange(sym)
        maxPos = fitModels[sym].maxPosition
        maxTradeSize = fitModels[sym].maxTradeSize
        liq = int(fitModels[sym].target.liquidity)
        normedPos = round(fitModels[sym].hOpt, 3)
        notionalPerLot = '${:,}'.format(fitModels[sym].notionalPerLot)
        targetNotional = fitModels[sym].notionalPerLot * targetPos  # findTargetExposure(fitModels, sym, targetPos)
        symTrade = [desc, targetNotional, normedPos, liq, currentPos, targetPos, maxPos, maxTradeSize,
                    notionalPerLot, refPrice, refTime, exchange, tradedSym]
        out.append(symTrade)
    out = pd.DataFrame(out, columns=cols).set_index('Description').sort_values('usdTargetNotional', ascending=False)
    out['usdTargetNotional'] = formatTargetExposure(out['usdTargetNotional'])

    return out


def formatTargetExposure(raw):
    return ['-${:,}'.format(abs(x)) if np.sign(x) < 0 else '${:,}'.format(x) for x in raw]


def createSummaryPaths(sumCSVs, timeSig):
    sumPaths = {}
    for investor in sumCSVs:
        os.makedirs(f"{logRoot}{investor}/summary/", exist_ok=True)
        sumPaths[investor] = f"{logRoot}{investor}/summary/{timeSig}.csv"
        sumCSVs[investor].to_csv(sumPaths[investor])
    return sumPaths


def isSummaryTime(timezone='US/Eastern'):
    localDT = datetime.datetime.now(pytz.timezone(timezone))
    if localDT.hour in summaryTimes:
        return True
    else:
        return False


def sendSummaryEmail(cfgs, fitModels, trades, execMD):
    if isSummaryTime():
        timeSig = execMD['timeSig']
        sumCSVs = createSummaryCSVs(cfgs, fitModels, trades, execMD)
        sumPaths = createSummaryPaths(sumCSVs, timeSig)
        sendFrom = "positions.afbi.cbct@sydneyquantitative.com"
        sendTo = ["matthew.ramanah@sydneyquantitative.com"]
        sendCC = ["christian.beulen@sydneyquantitative.com"]
        username = sendFrom
        password = "SydQuantPos23"
        subject = f"CSA Summary"
        gmail.sendSummaryFiles(sumPaths, sendFrom, sendTo, sendCC, username, password, subject, timeSig)
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
