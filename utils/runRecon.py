from pyConfig import *
from modules import md, utility, recon
from interfaces import common

cfg_file = root + "config/afbiRecon.json"
with open(cfg_file, 'r') as f:
    cfg = json.load(f)

symsToPlot = random.sample(cfg['targets'], 5) #cfg['targets'][0:20]
cfg['targets'] = symsToPlot
plot = True

# Initialisations
researchFeeds = utility.loadResearchFeeds(cfg)
seeds = utility.constructResearchSeeds(researchFeeds, cfg, location=0)
initPositions = recon.initialisePositions(cfg)
fitModels = common.initialiseModels(cfg, seeds=seeds, positions=initPositions, prod=False)

# Market Data
prodFeed = md.loadSyntheticMD(cfg, researchFeeds, maxUpdates=10000)

# Models
fitModels = recon.runRecon(prodFeed, fitModels, printRunTimes=False)

# Logs
prodLogs = recon.processLogs(fitModels)

if plot:
    recon.plotReconCols(cfg, prodLogs, researchFeeds, fitModels, symsToPlot=symsToPlot, model=True, alphas=False, preds=False)
    # recon.plotPnLs(prodLogs, researchFeeds, cfg)
