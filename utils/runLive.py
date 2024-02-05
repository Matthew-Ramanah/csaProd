from pyConfig import *
from modules import dataFeed, utility
from models.AFBI.interface import AFBI

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

send = False
saveModel = True
saveLogs = True

# Load Seeds
initSeeds = utility.loadInitSeeds(cfg)

# Load Positions & Limits
initPositions = AFBI.detectAFBIPositions(cfg)
riskLimits = AFBI.detectRiskLimits(cfg)

# Initialise models
fitModels = utility.initialiseModels(cfg, seeds=initSeeds, positions=initPositions, riskLimits=riskLimits, prod=True)

# Pull Market Data
md = dataFeed.feed(cfg).pullLatestMD(syntheticIncrement=0)

# Update Models
fitModels = utility.updateModels(fitModels, md)

# Generate tradeFile
trades = AFBI.generateAFBITradeFile(cfg, fitModels, md, initPositions, send=send, saveLogs=saveLogs)

if saveModel:
    modelState = utility.saveModelState(initSeeds, initPositions, md, trades, fitModels, saveLogs=saveLogs)

lg.info("Completed.")
