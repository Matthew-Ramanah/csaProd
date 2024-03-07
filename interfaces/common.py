from pyConfig import *
from modules import utility, gmail
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
        fitModels[investor] = utility.initialiseModels(cfgs[investor], seeds=initSeeds[investor],
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


def generateTradeFile(cfg, fitModels, md, initPositions, send, saveLogs):
    if cfg["investor"] == "AFBI":
        trades = AFBI.generateAFBITradeFile(cfg, fitModels, md, initPositions, send=send, saveLogs=saveLogs)
    else:
        raise ValueError("Unknown Investor")
    return trades


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
