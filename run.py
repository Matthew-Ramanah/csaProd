from pyConfig import *
from modules import md, utility, recon

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

researchFeeds = utility.loadResearchFeeds(cfg)
seeds = utility.constructSeeds(researchFeeds['recon'], cfg)
fitModels = utility.initialiseModels(cfg, seeds=seeds)

# Replace this with the live feed in production
prodFeed = md.loadSyntheticMD(cfg)
prodFeed = md.sampleFeed(prodFeed, researchFeeds, maxUpdates=10000)
lg.info("Feed Loaded.")

for i, md in prodFeed.iterrows():
    for sym in fitModels:
        fitModels[sym].mdUpdate(md)

        # Generate trades -> Apply tradeSizeCap from cfg here

        # Log

prodLogs = recon.processLogs(fitModels)
recon.plotReconCols(cfg, prodLogs, researchFeeds, fitModels)
# recon.reconcile(cfg, prodLogs, researchFeeds, fitModels)
