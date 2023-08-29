from pyConfig import *
from modules import syntheticMD, assets, utility


def initialiseModels(cfg, seeds):
    refData = utility.loadRefData()
    targets = []
    for target in cfg['targets']:
        targets.append(
            assets.traded(sym=target, cfg=cfg, params=cfg['fitParams'][target], refData=refData, seeds=seeds))

    return targets


with open(cfg_file, 'r') as f:
    cfg = json.load(f)
recon = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/recon.h5", key='recon', mode='r')

seeds = dict(recon.iloc[0])
seeds['lastTS'] = recon.iloc[0].name
targets = initialiseModels(cfg, seeds=seeds)

for target in targets:
    # Replace this with the live feed in production
    feed = syntheticMD.loadSyntheticMD(cfg, target.sym)
    for i, md in feed.iterrows():
        tgt.mdUpdate(md)
        print(i, md)
        # Generate trades -> Apply tradeSizeCap from cfg here

        # Log
lg.info("Completed")
