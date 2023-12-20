from pyConfig import *
from modules import md, utility, recon
from models.AFBI.interface import AFBI

cfg_file = root + "models/AFBI/config/ftiRemoved.json"
with open(cfg_file, 'r') as f:
    cfg = json.load(f)

researchFeeds = utility.loadResearchFeeds(cfg)
seeds = utility.constructResearchSeeds(researchFeeds, cfg)
initPositions = recon.initialisePositions(cfg)
riskLimits = cfg['fitParams']['basket']['riskLimits']
fitModels = utility.initialiseModels(cfg, seeds=seeds, positions=initPositions, riskLimits=riskLimits,
                                     timezone=AFBI.timezone, prod=False)

# Replace this with the live feed in production
prodFeed = md.loadSyntheticMD(cfg)
prodFeed = md.sampleFeed(prodFeed, researchFeeds, maxUpdates=5)
lg.info("Feed Loaded.")

fitModels, prodLogs, md = recon.runRecon(prodFeed, fitModels, printRunTimes=False)

if False:
    recon.plotReconCols(cfg, prodLogs, researchFeeds, fitModels)
    recon.plotPnLDeltas(prodLogs, researchFeeds, cfg)
    # recon.plotPnLs(prodLogs, researchFeeds, cfg)
    # recon.reconcile(prodLogs, researchFeeds, fitModels)
