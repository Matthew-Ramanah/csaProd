from pyConfig import *
from modules import utility
from interfaces import AFBI


def findRefPrice(md, sym):
    tradedSym = utility.findIqfTradedSym(sym)
    if sym in list(priceMultipliers.keys()):
        return round(priceMultipliers[sym] * md[f'{tradedSym}_close'], noDec)
    return md[f'{tradedSym}_close']


def detectPositions(cfg):
    if cfg["investor"] == "AFBI":
        initPositions = AFBI.detectAFBIPositions(cfg)
    else:
        raise ValueError("Unknown Investor")
    return initPositions


def generateTradeFile(cfg, fitModels, md, initPositions, send, saveLogs):
    if cfg["investor"] == "AFBI":
        trades = AFBI.generateAFBITradeFile(cfg, fitModels, md, initPositions, send=send, saveLogs=saveLogs)
    else:
        raise ValueError("Unknown Investor")
    return trades

def findNotionalExposure(fitModels, sym, targetPos):
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
