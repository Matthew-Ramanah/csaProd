from pyConfig import *
from modules import dataFeed, utility
from interfaces import common

# Run-time options
cfgFiles = ['qubeRecon', 'expandedRecon']

send = False
saveModel = False
saveLogs = False

# Initialise
cfgs = common.detectConfigs(cfgFiles)
initSeeds, initPositions, fitModels = common.initialiseSystems(cfgs)

# Pull Market Data
md = dataFeed.feed(cfgs).pullLatestMD(syntheticIncrement=0)

# Update Models
fitModels = utility.updateModels(fitModels, md)

if False:
    # Generate Output Files
    # Pull data for execution symbols
    trades = common.generateTradeFile(cfg, fitModels, md, initPositions, send=send, saveLogs=saveLogs)

    if saveModel:
        modelState = utility.saveModelState(cfg, initSeeds, initPositions, md, trades, fitModels, saveLogs=saveLogs)

lg.info("Completed.")
