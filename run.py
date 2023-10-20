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
prodFeed = md.sampleFeed(prodFeed, researchFeeds, maxUpdates=5000)
lg.info("Feed Loaded.")
runTimes = []
for i, md in prodFeed.iterrows():
    t0 = time.time()
    for sym in fitModels:
        fitModels[sym].mdUpdate(md)

    t1 = time.time()
    runTimes.append(1000 * (t1 - t0))
lg.info(f"Processed {len(prodFeed):,} Updates")
print(
    f'Tick2Trade Mean: {round(statistics.mean(runTimes), 2)} ms. Max: {round(max(runTimes), 2)} ms. Min: {round(min(runTimes), 2)}')
prodLogs = recon.processLogs(fitModels)

recon.plotReconCols(cfg, prodLogs, researchFeeds, fitModels)
recon.plotPnLs(prodLogs, researchFeeds, cfg)
#recon.reconcile(prodLogs, researchFeeds, fitModels)

sym = 'ZL0'
print(prodLogs[sym]['CL0'].iloc[np.where(prodLogs[sym]['CL0']['CL0_contractChange']==True)])