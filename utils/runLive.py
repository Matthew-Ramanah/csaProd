from pyConfig import *
from modules import dataFeed, utility
from interfaces import common

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

send = False
saveModel = True
saveLogs = False

# Load Seeds
initSeeds = utility.loadInitSeeds(cfg)

# Load Positions & Limits
initPositions = common.detectPositions(cfg)

# Initialise models
fitModels = utility.initialiseModels(cfg, seeds=initSeeds, positions=initPositions, prod=True)

# Pull Market Data
md = dataFeed.feed(cfg).pullLatestMD(syntheticIncrement=1)

# Update Models
fitModels = utility.updateModels(fitModels, md)

# Generate tradeFile
trades = common.generateTradeFile(cfg, fitModels, md, initPositions, send=send, saveLogs=saveLogs)

if saveModel:
    modelState = utility.saveModelState(cfg, initSeeds, initPositions, md, trades, fitModels, saveLogs=saveLogs)

lg.info("Completed.")
