from pyConfig import *
from modules import models, dataFeed


@functools.cache
def findSmoothFactor(invTau, decay):
    return np.exp(-invTau * decay)


def emaUpdate(lastValue, thisValue, decay, invTau):
    alpha = findSmoothFactor(invTau, decay)
    return alpha * lastValue + (1 - alpha) * thisValue


def loadRefData():
    refData = pd.read_csv(f'{root}asaRefData.csv')
    return refData.set_index('symbol')


def loadResearchFeeds(cfg):
    lg.info("Loading Research Feeds...")
    researchFeeds = {}
    researchFeeds['recon'] = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/recon.h5", key='recon', mode='r')
    for sym in cfg['targets']:
        researchFeeds[sym] = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/{sym}/featsSelected.h5", key='featsSelected',
                                         mode='r')
    return researchFeeds


def initialiseModels(cfg, seeds, positions, riskLimits, timezone, prod=False):
    refData = loadRefData()
    fitModels = {}
    for sym in cfg['targets']:
        fitModels[sym] = models.assetModel(targetSym=sym, cfg=cfg, params=cfg['fitParams'][sym], refData=refData,
                                           seeds=seeds, initHoldings=positions[sym], riskLimits=riskLimits,
                                           timezone=timezone, prod=prod)
    lg.info("Models Initialised.")
    return fitModels


def findNotionalFx(target):
    refData = loadRefData()
    return refData.loc[target]['notionalCurrency']


def findFeatPred(ft, target):
    partitions = ft.replace(f'feat_{target}_', '').split('_')
    if len(partitions) == 4:
        return partitions[0]
    else:
        return f'{partitions[0]}_{partitions[1]}'


def findBasisFrontSym(backSym):
    return backSym.replace('1', '0')


def constructResearchSeeds(researchFeeds, cfg, location=0):
    """
    Seed in models using researchFeeds
    Location=0 is used for reconciling
    Location=-1 is used to seed production models with latest research data
    """
    seeds = {}
    for target in cfg['targets']:
        seeds[target] = {}
        seeds[target] = {f'{target}_midPrice': researchFeeds[target][f'{target}_midPrice'].iloc[location],
                         f'Volatility_{target}': researchFeeds[target][f'Volatility_{target}'].iloc[location],
                         f'{target}_lastTS': researchFeeds[target][f'{target}_lastTS'].iloc[location].strftime(
                             '%Y_%m_%d_%H'),
                         f'{target}_symbol': researchFeeds[target][f'{target}_symbol'].iloc[location]}

        for ft in cfg['fitParams'][target]['feats']:
            pred = findFeatPred(ft, target)
            seeds[target][f'{pred}_midPrice'] = researchFeeds[target][f'{pred}_midPrice'].iloc[location]
            seeds[target][f'Volatility_{pred}'] = researchFeeds[target][f'Volatility_{pred}'].iloc[location]
            seeds[target][f'{pred}_symbol'] = researchFeeds[target][f'{pred}_symbol'].iloc[location]
            seeds[target][f'{pred}_lastTS'] = researchFeeds[target][f'{pred}_lastTS'].iloc[location].strftime(
                '%Y_%m_%d_%H')

            ftType = ft.split('_')[-3]
            if ftType == "Basis":
                frontSym = findBasisFrontSym(pred)
                seeds[target][f'{frontSym}_midPrice'] = researchFeeds[target][f'{frontSym}_midPrice'].iloc[location]
                seeds[target][f'Volatility_{frontSym}'] = researchFeeds[target][f'Volatility_{frontSym}'].iloc[location]
                seeds[target][f'{frontSym}_symbol'] = researchFeeds[target][f'{frontSym}_symbol'].iloc[location]
                seeds[target][f'{frontSym}_lastTS'] = researchFeeds[target][f'{frontSym}_lastTS'].iloc[
                    location].strftime('%Y_%m_%d_%H')

            name = ft.replace('feat_', '')
            seeds[target][f'{name}_smoothSeed'] = researchFeeds[target][f'{name}_Smooth'].iloc[location]
            seeds[target][f'{name}_zSeed'] = researchFeeds[target][f'{name}_Z'].iloc[location]
            seeds[target][f'{name}_volSeed'] = researchFeeds[target][f'{name}_Std'].iloc[location]

        fx = findNotionalFx(target)
        if fx != 'USD':
            seeds[target][f'{fx}=_midPrice'] = researchFeeds[target][f'{fx}=_midPrice'].iloc[location]
            seeds[target][f'Volatility_{fx}='] = researchFeeds[target][f'Volatility_{fx}='].iloc[location]
            seeds[target][f'{fx}=_symbol'] = researchFeeds[target][f'{fx}=_symbol'].iloc[location]
            seeds[target][f'{fx}=_lastTS'] = researchFeeds[target][f'{fx}=_lastTS'].iloc[location].strftime(
                '%Y_%m_%d_%H')

    return seeds


def saveModelState(initSeeds, initPositions, md, trades, fitModels, saveLogs=True):
    modelState = {
        "initSeeds": initSeeds,
        "initPositions": initPositions,
        "trades": trades,
        "seedDump": {},
        "logs": {},
        "alphasLog": {}
    }

    for sym in fitModels:
        modelState['seedDump'][sym] = fitModels[sym].seedDump
        modelState['logs'][sym] = fitModels[sym].log[-1]
        modelState['alphasLog'][sym] = fitModels[sym].alphasLog

    with open(f'{interfaceRoot}modelState.json', 'w') as f:
        json.dump(modelState, f)
    lg.info("Saved Model State.")

    if saveLogs:
        with open(f"{logRoot}models/CBCT_{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["logs"], f)

        with open(f"{logRoot}alphas/CBCT_{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["alphasLog"], f)
        lg.info("Saved Logs.")

    return modelState


def generateTrades(fitModels):
    trades = {}
    for sym in fitModels:
        trades[sym] = int(fitModels[sym].tradeVolume)

    return trades


def createTimeSig(timezone='UTC'):
    timeSig = datetime.datetime.now(pytz.timezone(timezone)).strftime('%Y_%m_%d_%H')
    return timeSig


def localizeTS(stringTS, timezone):
    return pytz.timezone(timezone).localize(pd.Timestamp(stringTS))


def formatTsSeed(tsSeed, timezone):
    tsNaive = pd.Timestamp(datetime.datetime.strptime(tsSeed, '%Y_%m_%d_%H'))
    return localizeTS(tsNaive, timezone)


def formatTsToStrig(ts):
    return ts.strftime('%Y_%m_%d_%H')


def loadInitSeeds(cfg):
    """
    Load Seed Dump if it exists, else seed with research seeds
    """
    try:
        with open(f'{interfaceRoot}modelState.json', 'r') as f:
            oldModelState = json.load(f)
        return oldModelState['seedDump']
    except:
        lg.info("Can't find previous modelState, seeding with latest research data")
        researchFeeds = loadResearchFeeds(cfg)
        return constructResearchSeeds(researchFeeds, cfg)


def findPositionDelay(lastPosTime, timezone):
    return pd.Timestamp(datetime.datetime.now(pytz.timezone(timezone))) - lastPosTime.tz_localize(timezone)


def findDaysHoursMinutes(positionDelay):
    days, r1 = divmod(positionDelay.total_seconds(), 86400)
    hours, r2 = divmod(r1, 3600)
    minutes, seconds = divmod(r2, 60)
    return days, hours, minutes


def logPositionDelay(lastPosTime, timezone):
    positionDelay = findPositionDelay(lastPosTime, timezone)
    days, hours, minutes = findDaysHoursMinutes(positionDelay)
    lg.info(f"Position File Updated {int(days)} Days, {int(hours)} Hours, {int(minutes)} Minutes Ago.")
    return


def updateModels(fitModels, md):
    for sym in fitModels:
        fitModels[sym].mdUpdate(md)

    dataFeed.monitorMdhSanity(fitModels, md)
    return fitModels
