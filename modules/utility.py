from pyConfig import *
from modules import assets, models


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
        researchFeeds[sym] = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/{sym}/featsSelected.h5", key='featsSelected', mode='r')
    return researchFeeds


def initialiseModels(cfg, seeds):
    refData = loadRefData()
    fitModels = {}
    for sym in cfg['targets']:
        fitModels[sym] = models.assetModel(targetSym=sym, cfg=cfg, params=cfg['fitParams'][sym], refData=refData,
                                           seeds=seeds)
    lg.info("Models Initialised.")
    return fitModels


def constructSeeds(reconFeed, cfg):
    seeds = dict(reconFeed.iloc[0])
    seeds['lastTS'] = reconFeed.iloc[0].name

    lg.info("Setting zSeed, smoothSeed for all feats to 0 for now. VolSeeds set to 100")
    for target in cfg['targets']:
        for ft in cfg['fitParams'][target]['feats']:
            name = ft.replace('feat_', '')
            seeds[f'{name}_zSeed'] = 0
            seeds[f'{name}_smoothSeed'] = 0
            seeds[f'{name}_volSeed'] = 100
    return seeds


def findBasisFrontSym(backSym):
    return backSym.replace('1', '0')
