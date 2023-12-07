from pyConfig import *
from modules import dataFeed, utility
from models.AFBI.interface import AFBI

with open(cfg_file, 'r') as f:
    cfg = json.load(f)
timezone = 'US/Eastern'

# Load Seeds
initSeeds = utility.loadInitSeeds(cfg)

# Load Positions
initPositions = AFBI.detectAFBIPositions(cfg)

# Initialise models
fitModels = utility.initialiseModels(cfg, seeds=initSeeds, positions=initPositions, timezone=timezone, prod=True)

# Pull Market Data
md = dataFeed.feed(cfg, timezone).pullLatestMD(syntheticIncrement=0)

# Update Models
for sym in fitModels:
    fitModels[sym].mdUpdate(md)

# Generate tradeFile
trades = AFBI.generateAFBITradeFile(fitModels, md, initPositions, timezone, send=False)

# Save
modelState = utility.saveModelState(initSeeds, initPositions, md, trades, fitModels)

lg.info("Completed.")

print("")
for sym in fitModels:
    print(sym, fitModels[sym].normedHoldings)
