from pyConfig import *
from modules import models


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
    researchFeeds = {}
    researchFeeds['recon'] = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/recon.h5", key='recon', mode='r')
    for sym in cfg['targets']:
        researchFeeds[sym] = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/{sym}/featsSelected.h5", key='featsSelected',
                                         mode='r')
    return researchFeeds


def initialiseModels(cfg, seeds, positions, prod=False):
    refData = loadRefData()
    fitModels = {}
    for sym in cfg['targets']:
        fitModels[sym] = models.assetModel(targetSym=sym, cfg=cfg, params=cfg['fitParams'][sym], refData=refData,
                                           seeds=seeds, initHoldings=positions[sym], prod=prod)
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
                         f'{target}_lastTS': str(researchFeeds[target][f'{target}_lastTS'].iloc[location].date()),
                         f'{target}_symbol': researchFeeds[target][f'{target}_symbol'].iloc[location]}

        for ft in cfg['fitParams'][target]['feats']:
            pred = findFeatPred(ft, target)
            seeds[target][f'{pred}_midPrice'] = researchFeeds[target][f'{pred}_midPrice'].iloc[location]
            seeds[target][f'Volatility_{pred}'] = researchFeeds[target][f'Volatility_{pred}'].iloc[location]
            seeds[target][f'{pred}_symbol'] = researchFeeds[target][f'{pred}_symbol'].iloc[location]

            ftType = ft.split('_')[-3]
            if ftType == "Basis":
                frontSym = findBasisFrontSym(pred)
                seeds[target][f'{frontSym}_midPrice'] = researchFeeds[target][f'{frontSym}_midPrice'].iloc[location]
                seeds[target][f'Volatility_{frontSym}'] = researchFeeds[target][f'Volatility_{frontSym}'].iloc[location]
                seeds[target][f'{frontSym}_symbol'] = researchFeeds[target][f'{frontSym}_symbol'].iloc[location]

            name = ft.replace('feat_', '')
            seeds[target][f'{name}_smoothSeed'] = researchFeeds[target][f'{name}_Smooth'].iloc[location]
            seeds[target][f'{name}_zSeed'] = researchFeeds[target][f'{name}_Z'].iloc[location]
            seeds[target][f'{name}_volSeed'] = researchFeeds[target][f'{name}_Std'].iloc[location]

        fx = findNotionalFx(target)
        if fx != 'USD':
            seeds[target][f'{fx}=_midPrice'] = researchFeeds[target][f'{fx}=_midPrice'].iloc[location]
            seeds[target][f'Volatility_{fx}='] = researchFeeds[target][f'Volatility_{fx}='].iloc[location]
            seeds[target][f'{fx}=_symbol'] = researchFeeds[target][f'{fx}=_symbol'].iloc[location]

    return seeds


def saveModelState(initSeeds, initPositions, md, trades, fitModels):
    modelState = {
        "initSeeds": initSeeds,
        "initPositions": initPositions,
        "md": dict(md),
        "trades": trades,
        "seedDump": {},
        "logs": {}
    }

    for sym in fitModels:
        modelState['seedDump'][sym] = fitModels[sym].seedDump
        modelState['logs'][sym] = fitModels[sym].log

    with open(f'{interfaceRoot}modelState.json', 'w') as f:
        json.dump(modelState, f)

    lg.info("Saved Model State.")
    return modelState


def generateTrades(fitModels):
    trades = {}
    for sym in fitModels:
        trades[sym] = int(fitModels[sym].tradeVolume)

    return trades
