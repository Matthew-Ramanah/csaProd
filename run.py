from pyConfig import *
from modules import syntheticMD, assets, utility


def initialiseModels(cfg, seeds):
    refData = utility.loadRefData()
    targets = []
    for target in cfg['targets']:
        targets.append(
            assets.traded(sym=target, cfg=cfg, params=cfg['fitParams'][target], refData=refData, seeds=seeds))

    return targets



seeds = {f'Volatility_timeDR_ZL0': 1000}

with open(cfg_file, 'r') as f:
    cfg = json.load(f)
recon = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/recon.h5", key='data', mode='r')
stats = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/recon.h5", key='stats', mode='r')
targets = initialiseModels(cfg, seeds=seeds)

for target in targets:
    # Replace this with the live feed in production
    feed = syntheticMD.loadSyntheticMD(cfg, target)
    for i, md in feed.iterrows():
        target.mdUpdate(md)

        # Generate trades -> Apply tradeSizeCap from cfg here

        # Log
lg.info("Completed")
