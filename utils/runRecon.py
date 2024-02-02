from pyConfig import *
from modules import md, utility, recon

cfg_file = root + "models/AFBI/config/iqfRecon.json"
with open(cfg_file, 'r') as f:
    cfg = json.load(f)

symsToPlot = cfg['targets'][0:5]
cfg['targets'] = symsToPlot
plot = True

target = cfg['targets'][0]
pred = 'QCL#'

# Initialisations
researchFeeds = utility.loadResearchFeeds(cfg)
seeds = utility.constructResearchSeeds(researchFeeds, cfg)
initPositions = recon.initialisePositions(cfg)
riskLimits = cfg['fitParams']['basket']['riskLimits']
fitModels = utility.initialiseModels(cfg, seeds=seeds, positions=initPositions, riskLimits=riskLimits, prod=False)

# Market Data
prodFeed = md.loadSyntheticMD(cfg, researchFeeds, maxUpdates=5000)

# Models
fitModels = recon.runRecon(prodFeed, fitModels, printRunTimes=False)

# Logs
prodLogs = recon.processLogs(fitModels)

if plot:
    recon.plotReconCols(cfg, prodLogs, researchFeeds, fitModels, symsToPlot=symsToPlot)
    recon.plotPnLs(prodLogs, researchFeeds, cfg)
