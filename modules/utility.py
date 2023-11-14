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


def initialiseModels(cfg, seeds):
    refData = loadRefData()
    fitModels = {}
    for sym in cfg['targets']:
        fitModels[sym] = models.assetModel(targetSym=sym, cfg=cfg, params=cfg['fitParams'][sym], refData=refData,
                                           seeds=seeds)
    lg.info("Models Initialised.")
    return fitModels


def findFeatPred(ft, target):
    partitions = ft.replace(f'feat_{target}_', '').split('_')
    if len(partitions) == 4:
        return partitions[0]
    else:
        return f'{partitions[0]}_{partitions[1]}'


def constructSeeds(researchFeeds, cfg):
    # seeds = dict(researchFeeds['recon'].iloc[0])
    # seeds['lastTS'] = researchFeeds['recon'].iloc[0].name
    seeds = {}
    for target in cfg['targets']:
        seeds[target] = {}
        seeds[target] = {f'{target}_midPrice': researchFeeds[target][f'{target}_midPrice'].iloc[0],
                         f'Volatility_{target}': researchFeeds[target][f'Volatility_{target}'].iloc[0]}

        for ft in cfg['fitParams'][target]['feats']:
            pred = findFeatPred(ft, target)
            seeds[target][f'{pred}_midPrice'] = researchFeeds[target][f'{pred}_midPrice'].iloc[0]
            seeds[target][f'Volatility_{pred}'] = researchFeeds[target][f'Volatility_{pred}'].iloc[0]

            ftType = ft.split('_')[-3]
            if ftType == "Basis":
                frontSym = findBasisFrontSym(pred)
                seeds[target][f'{frontSym}_midPrice'] = researchFeeds[target][f'{frontSym}_midPrice'].iloc[0]
                seeds[target][f'Volatility_{frontSym}'] = researchFeeds[target][f'Volatility_{frontSym}'].iloc[0]

            name = ft.replace('feat_', '')
            seeds[target][f'{name}_smoothSeed'] = researchFeeds[target][f'{name}_Smooth'].iloc[0]
            seeds[target][f'{name}_zSeed'] = researchFeeds[target][f'{name}_Z'].iloc[0]
            seeds[target][f'{name}_volSeed'] = researchFeeds[target][f'{name}_Std'].iloc[0]
    return seeds


def findBasisFrontSym(backSym):
    return backSym.replace('1', '0')


def loadRefData():
    refData = pd.read_csv(f'{root}asaRefData.csv')
    return refData.set_index('symbol')
