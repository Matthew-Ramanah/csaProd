from pyConfig import *
from modules import md, utility, recon

updatesToRecon = 10000

with open(cfg_file, 'r') as f:
    cfg = json.load(f)
researchFeed = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/recon.h5", key='recon', mode='r')
researchFeed = researchFeed.head(updatesToRecon)

seeds = utility.constructSeeds(researchFeed, cfg)
fitModels = utility.initialiseModels(cfg, seeds=seeds)

# Replace this with the live feed in production
feed = md.loadSyntheticMD(cfg)
feed = feed.head(updatesToRecon)
lg.info("Feed Loaded.")

for i, md in feed.iterrows():
    for sym in fitModels:
        fitModels[sym].mdUpdate(md)

        # Generate trades -> Apply tradeSizeCap from cfg here

        # Log

prodLogs = recon.processLogs(fitModels)
recon.reconcile(prodLogs, researchFeed, fitModels)
recon.plotReconCols(prodLogs, researchFeed, fitModels)
