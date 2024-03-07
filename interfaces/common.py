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
        lg.info(f"{investor} System Initialised.")

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


def sendTradeFiles(cfgs, initPositions, fitModels, execMD):
    for investor in cfgs:
        if investor == "AFBI":
            AFBI.sendAFBITradeFile(cfgs[investor], fitModels, execMD['timeSig'], initPositions)
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
    trades, execSyms = utility.detectTrades(fitModels)

    # Pull market data for execSyms
    execMD = mdPipe.pullExecMD(execSyms)

    # Send tradeFiles & summary
    if send:
        sendTradeFiles(cfgs, initPositions, fitModels, execMD)
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

        os.makedirs(f"{logRoot}models/", exist_ok=True)
        with open(f"{logRoot}models/{investor}/{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["logs"], f)

        os.makedirs(f"{logRoot}alphas/", exist_ok=True)
        with open(f"{logRoot}alphas/{investor}/{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["alphasLog"], f)
        lg.info("Saved Logs.")

        os.makedirs(f"{logRoot}seeds/", exist_ok=True)
        with open(f"{logRoot}seeds/{investor}/{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["seedDump"], f)

    return


def sendSummaryEmail(sumPaths, timeSig):
    sendFrom = "positions.afbi.cbct@sydneyquantitative.com"
    sendTo = ["matthew.ramanah@sydneyquantitative.com"]
    sendCC = []
    username = sendFrom
    password = "SydQuantPos23"
    subject = "CBCT Summary"
    message = f"CBCT_{timeSig}"
    filename = f"CBCT_{timeSig}.csv"
    # TODO - Parse multiple sumPaths in here
    gmail.sendFile(sumPath, sendFrom, sendTo, sendCC, username, password, subject, message, filename)
    return
