from pyConfig import *


@lru_cache(maxsize=16)
def findSmoothFactor(invTau, decay):
    return np.exp(-invTau * decay)


def emaUpdate(lastValue, thisValue, decay, invTau):
    alpha = findSmoothFactor(invTau, decay)
    return alpha * lastValue + (1 - alpha) * thisValue


def loadRefData():
    return pd.read_csv(f'{root}csaRefData.csv')


def loadResearchFeeds(cfg):
    researchFeeds = {}
    researchFeeds['recon'] = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/recon.h5", key='recon', mode='r')
    for sym in cfg['targets']:
        researchFeeds[sym] = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/{sym}/featsSelected.h5", key='featsSelected',
                                         mode='r')
    return researchFeeds


def findNotionalFx(target):
    refData = loadRefData()
    return refData.loc[refData['iqfUnadjusted'] == target]['notionalCurrency'].values[0]


def findFxSym(fx):
    refData = loadRefData()
    return refData.loc[refData['description'] == f'{fx}=']['iqfUnadjusted'].values[0]


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


def constructResearchSeeds(resFeed, cfg, location):
    """
    Seed in models using researchFeeds
    Location=0 is used for reconciling
    Location=-1 is used to seed production models with latest research data
    """
    seeds = {}
    for target in cfg['targets']:
        seeds[target] = {
            f"{target}_Liquidity": resFeed['recon'][f'{target}_Liquidity'].iloc[location],
            f"{target}_cumDailyVolume": resFeed['recon'][f'{target}_cumDailyVolume'].iloc[location]
        }
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


def detectTrades(fitModels):
    trades = {}
    for investor in fitModels:
        trades[investor] = {}
        for sym in fitModels[investor]:
            trades[investor][sym] = int(fitModels[investor][sym].tradeVolume)

    return trades


def createTimeSig(timezone='US/Eastern'):
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


def modelStatePath(cfg):
    if cfg["investor"] == "AFBI":
        return
    else:
        raise ValueError("Unknown Investor")


def loadInitSeeds(cfg):
    """
    Load Seed Dump if it exists, else seed with research seeds
    """
    try:
        with open(f"{interfaceRoot}states/{cfg['investor']}.json", 'r') as f:
            oldModelState = json.load(f)
        return oldModelState['seedDump']
    except:
        lg.info(f"Can't find {cfg['investor']} modelState, seeding with latest research data")
        researchFeeds = loadResearchFeeds(cfg)
        return constructResearchSeeds(researchFeeds, cfg, location=-1)


def findPositionDelay(lastPosTime, timezone):
    return pd.Timestamp(datetime.datetime.now(pytz.timezone(timezone))) - lastPosTime.tz_localize(timezone)


def findDaysHoursMinutes(positionDelay):
    days, r1 = divmod(positionDelay.total_seconds(), 86400)
    hours, r2 = divmod(r1, 3600)
    minutes, seconds = divmod(r2, 60)
    return days, hours, minutes


def logPositionDelay(lastPosTime, timezone, investor):
    positionDelay = findPositionDelay(lastPosTime, timezone)
    days, hours, minutes = findDaysHoursMinutes(positionDelay)
    lg.info(f"{investor} Position File Updated {int(days)} Days, {int(hours)} Hours, {int(minutes)} Minutes Ago.")
    return


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


def findIqfTradedSym(sym):
    refData = loadRefData()
    return refData.loc[refData['iqfUnadjusted'] == sym]['iqfTradedSym'].values[0]


def findDescription(sym):
    refData = loadRefData()
    return refData.loc[refData['iqfUnadjusted'] == sym]['description'].values[0]


def findExchange(sym):
    refData = loadRefData()
    return refData.loc[refData['iqfUnadjusted'] == sym]['exchange'].values[0]


def isAdjSym(sym):
    refData = loadRefData()
    adjSyms = list(refData['iqfAdjusted'].values)
    if sym in adjSyms:
        return True
    return False

def findIqfTradedSyms():
    refData = loadRefData()
    return list(refData['iqfTradedSym'].dropna().values)