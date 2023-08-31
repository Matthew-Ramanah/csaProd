from pyConfig import *
from modules import syntheticMD, utility, recon

with open(cfg_file, 'r') as f:
    cfg = json.load(f)
researchFeed = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/recon.h5", key='recon', mode='r')
researchFeed = researchFeed.head(1000)

seeds = utility.constructSeeds(researchFeed, cfg)
models = utility.initialiseModels(cfg, seeds=seeds)

# Replace this with the live feed in production
feed = syntheticMD.loadSyntheticMD(cfg)
feed = feed.head(1000)
lg.info("Feed Loaded.")

for i, md in feed.iterrows():
    for sym in models:
        models[sym].mdUpdate(md)
        # lg.info(f'{target.sym} hOpt: {target.hOpt}')

        # Generate trades -> Apply tradeSizeCap from cfg here

        # Log


prodLogs = recon.processLogs(models)

sym = 'ZC0'
self = models[sym]
log = prodLogs[sym]

plt.figure()
plt.plot(researchFeed[f'{sym}_midPrice'], label='research')
plt.plot(log[f'{sym}_midPrice'], label='prod')
plt.legend()
plt.show()

recon.reconcile(prodLogs, researchFeed, models)