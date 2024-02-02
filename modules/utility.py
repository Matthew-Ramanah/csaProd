from pyConfig import *
from modules import models, dataFeed


def findSmoothFactor(invTau, decay):
    return np.exp(-invTau * decay)


def emaUpdate(lastValue, thisValue, decay, invTau):
    alpha = findSmoothFactor(invTau, decay)
    return alpha * lastValue + (1 - alpha) * thisValue


def loadRefData():
    return pd.read_csv(f'{root}csaRefData.csv')


def loadResearchFeeds(cfg):
    lg.info("Loading Research Feeds...")
    researchFeeds = {}
    researchFeeds['recon'] = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/recon.h5", key='recon', mode='r')
    for sym in cfg['targets']:
        researchFeeds[sym] = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/{sym}/featsSelected.h5", key='featsSelected',
                                         mode='r')
    return researchFeeds


def initialiseModels(cfg, seeds, positions, riskLimits, prod=False):
    fitModels = {}
    for sym in cfg['targets']:
        fitModels[sym] = models.assetModel(targetSym=sym, cfg=cfg, params=cfg['fitParams'][sym], seeds=seeds,
                                           initHoldings=positions[sym], riskLimits=riskLimits, prod=prod)
    lg.info("Models Initialised.")
    return fitModels


def findNotionalFx(target):
    refData = loadRefData()
    return refData.loc[refData['iqfUnadjusted'] == target]['notionalCurrency'].values[0]


def findFxSym(fx):
    refData = loadRefData()
    return refData.loc[refData['description'] == f'{fx}=']['iqfUnadjusted'].values[0]


def findBasisFrontSym(backSym):
    return backSym.replace('1', '0')


def findFtSyms(target, ft):
    partitions = ft.replace(f'feat_{target}_', '').split('_')
    return partitions[0].split('-')


def findSymsNeeded(cfg, target):
    symsNeeded = [target]
    for ft in cfg['fitParams'][target]['feats']:
        symsNeeded += findFtSyms(target, ft)

    fx = findNotionalFx(target)
    if fx != 'USD':
        symsNeeded += [findFxSym(fx)]
    return list(set(symsNeeded))


def constructResearchSeeds(resFeed, cfg, location=0):
    """
    Seed in models using researchFeeds
    Location=0 is used for reconciling
    Location=-1 is used to seed production models with latest research data
    """
    seeds = {}
    for target in cfg['targets']:
        seeds[target] = {}
        symsNeeded = findSymsNeeded(cfg, target)
        for sym in symsNeeded:
            seeds[target][f'{sym}_close'] = resFeed[target][f'{sym}_close'].iloc[location]
            seeds[target][f'{sym}_Volatility'] = resFeed[target][f'{sym}_Volatility'].iloc[location]
            seeds[target][f'{sym}_lastTS'] = resFeed[target][f'{sym}_lastTS'].iloc[location].strftime('%Y_%m_%d_%H')

        for ft in cfg['fitParams'][target]['feats']:
            name = ft.replace('feat_', '')
            seeds[target][f'{name}_smoothSeed'] = resFeed[target][f'{name}_Smooth'].iloc[location]
            seeds[target][f'{name}_zSeed'] = resFeed[target][f'{name}_Z'].iloc[location]
            seeds[target][f'{name}_volSeed'] = resFeed[target][f'{name}_Std'].iloc[location]

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
        os.makedirs(f"{logRoot}models/", exist_ok=True)
        with open(f"{logRoot}models/CBCT_{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["logs"], f)

        os.makedirs(f"{logRoot}alphas/", exist_ok=True)
        with open(f"{logRoot}alphas/CBCT_{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["alphasLog"], f)
        lg.info("Saved Logs.")

        os.makedirs(f"{logRoot}seeds/", exist_ok=True)
        with open(f"{logRoot}seeds/CBCT_{md['timeSig']}.json", 'w') as f:
            json.dump(modelState["seedDump"], f)

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


def findTsSeedDate(tsSeed):
    return formatStringToTs(tsSeed).date()


def formatStringToTs(tsString):
    return pd.Timestamp(datetime.datetime.strptime(tsString, '%Y_%m_%d_%H'))


def formatTsToString(ts):
    return ts.strftime('%Y_%m_%d_%H')


def loadInitSeeds(cfg, paper=False):
    """
    Load Seed Dump if it exists, else seed with research seeds
    """
    try:
        _, filename = findLogDirFileName(paper)

        with open(f'{interfaceRoot}{filename}.json', 'r') as f:
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


def findLogDirFileName(paper):
    if not paper:
        logDir = logRoot
        filename = 'modelState'
    else:
        logDir = paperLogRoot
        filename = 'paperState'
    return logDir, filename


def findTickSize(target):
    refData = loadRefData()
    return float(refData.loc[refData['iqfUnadjusted'] == target]['tickSize'].values[0])

def findTickValue(target):
    refData = loadRefData()
    return float(refData.loc[refData['iqfUnadjusted'] == target]['tickValue'].values[0])

def findAssetClass(target):
    refData = loadRefData()
    return refData.loc[refData['iqfUnadjusted'] == target]['assetClass'].values[0]

def findEffSpread(target):
    refData = loadRefData()
    return float(refData.loc[refData['iqfUnadjusted'] == target]['effSpread'].values[0])


def findNotionalMultiplier(target):
    refData = loadRefData()
    return float(refData.loc[refData['iqfUnadjusted'] == target]['notionalMultiplier'].values[0])


def findAdjSym(sym):
    refData = loadRefData()
    return refData.loc[refData['iqfUnadjusted'] == sym]['iqfAdjusted'].values[0]
