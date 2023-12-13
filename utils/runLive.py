from pyConfig import *
from modules import dataFeed, utility
from models.AFBI.interface import AFBI

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

# Load Seeds
initSeeds = utility.loadInitSeeds(cfg)

# Load Positions & Limits
initPositions = AFBI.detectAFBIPositions(cfg)
riskLimits = AFBI.detectRiskLimits(cfg)

# Initialise models
fitModels = utility.initialiseModels(cfg, seeds=initSeeds, positions=initPositions, riskLimits=riskLimits,
                                     timezone=AFBI.timezone, prod=True)

# Pull Market Data
md = dataFeed.feed(cfg, AFBI.timezone).pullLatestMD(syntheticIncrement=0)

# Update Models
fitModels = utility.updateModels(fitModels, md)

# Generate tradeFile
trades = AFBI.generateAFBITradeFile(fitModels, md, initPositions, AFBI.timezone, send=False)

# Save
modelState = utility.saveModelState(initSeeds, initPositions, md, trades, fitModels)

lg.info("Completed.")
