from pyConfig import *
from modules import syntheticMD, utility

with open(cfg_file, 'r') as f:
    cfg = json.load(f)
recon = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/recon.h5", key='recon', mode='r')
recon = recon.head(50)

seeds = utility.constructSeeds(recon, cfg)
models = utility.initialiseModels(cfg, seeds=seeds)

# Replace this with the live feed in production
feed = syntheticMD.loadSyntheticMD(cfg)
feed = feed.head(50)
lg.info("Feed Loaded.")

for i, md in feed.iterrows():
    lg.info(f"Update: {i}")
    for sym in models:
        models[sym].mdUpdate(md)
        # lg.info(f'{target.sym} hOpt: {target.hOpt}')

        # Generate trades -> Apply tradeSizeCap from cfg here

        # Log

logs = {}
for sym in models:
    logs[sym] = pd.DataFrame(models[sym].log,
                             columns=['lastTS', 'sym', 'contractChange', 'bidPrice', 'askPrice', 'bidSize', 'askSize',
                                      'midPrice', 'microPrice', 'timeDecay', 'vol', 'annPctChange', 'cumAlpha',
                                      'hOpt', 'holdings'])
lg.info("Completed")
sym = 'ZC0'
self = models[sym]
log = logs[sym]
print(log)