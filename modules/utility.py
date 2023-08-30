from pyConfig import *
from modules import assets


def emaUpdate(lastValue, thisValue, decay, invTau):
    alpha = np.exp(-invTau * decay)
    return alpha * thisValue + (1 - alpha) * lastValue


def loadRefData():
    refData = pd.read_csv(f'{root}asaRefData.csv')
    return refData.set_index('symbol')


def initialiseModels(cfg, seeds):
    refData = loadRefData()
    targets = []
    for target in cfg['targets']:
        targets.append(
            assets.traded(sym=target, cfg=cfg, params=cfg['fitParams'][target], refData=refData, seeds=seeds))
    lg.info("Models Initialised.")
    return targets


def constructSeeds(recon, cfg):
    seeds = dict(recon.iloc[0])
    seeds['lastTS'] = recon.iloc[0].name

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
