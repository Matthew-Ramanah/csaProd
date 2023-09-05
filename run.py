from pyConfig import *
from modules import md, utility, recon

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

researchFeeds = utility.loadResearchFeeds(cfg)
seeds = utility.constructSeeds(researchFeeds, cfg)
fitModels = utility.initialiseModels(cfg, seeds=seeds)
researchFeeds = recon.constructTimeDeltas(fitModels, researchFeeds)

# Replace this with the live feed in production
prodFeed = md.loadSyntheticMD(cfg)
prodFeed = md.sampleFeed(prodFeed, researchFeeds, maxUpdates=100000)
lg.info("Feed Loaded.")
t0 = time.time()
for i, md in prodFeed.iterrows():
    for sym in fitModels:
        fitModels[sym].mdUpdate(md)

        # Generate trades -> Apply tradeSizeCap from cfg here

t1 = time.time()
lg.info(f"Processed {len(prodFeed):,} Updates with mean time: {round(1000 * (t1 - t0) / len(prodFeed), 2)} ms")
prodLogs = recon.processLogs(fitModels)
recon.plotReconCols(cfg, prodLogs, researchFeeds, fitModels)
# recon.reconcile(prodLogs, researchFeeds, fitModels)

# print(prodLogs['ZL0']['ZL0_IND0_RV_timeDR_146'].tail(20))
