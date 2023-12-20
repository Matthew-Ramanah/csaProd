from pyConfig import *
from modules import md, utility, recon
from models.AFBI.interface import AFBI

cfg_file = root + "models/AFBI/config/ftiRemoved.json"
with open(cfg_file, 'r') as f:
    cfg = json.load(f)

plot = False

# Initialisations
researchFeeds = utility.loadResearchFeeds(cfg)
seeds = utility.constructResearchSeeds(researchFeeds, cfg)
initPositions = recon.initialisePositions(cfg)
riskLimits = cfg['fitParams']['basket']['riskLimits']
fitModels = utility.initialiseModels(cfg, seeds=seeds, positions=initPositions, riskLimits=riskLimits,
                                     timezone=AFBI.timezone, prod=False)

# Market Data
prodFeed = md.loadSyntheticMD(cfg, researchFeeds, maxUpdates=5)

# Models
fitModels = recon.runRecon(prodFeed, fitModels, printRunTimes=False)

# Logs
prodLogs = recon.processLogs(fitModels)

if plot:
    recon.plotReconCols(cfg, prodLogs, researchFeeds, fitModels)
    recon.plotPnLDeltas(prodLogs, researchFeeds, cfg)
    recon.plotPnLs(prodLogs, researchFeeds, cfg)
