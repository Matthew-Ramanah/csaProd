from pyConfig import *
from modules import dataFeed, utility
from models.AFBI.interface import AFBI

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

# Load Seeds
initSeeds = utility.loadInitSeeds(cfg)

# Load Positions
initPositions = AFBI.detectAFBIPositions(cfg)

# Initialise models
fitModels = utility.initialiseModels(cfg, seeds=initSeeds, positions=initPositions, timezone=AFBI.timezone, prod=True)

# Pull Market Data
md = dataFeed.feed(cfg, AFBI.timezone).pullLatestMD(syntheticIncrement=0)

# Update Models
for sym in fitModels:
    fitModels[sym].mdUpdate(md)

# Check Bad Data
for sym in fitModels:
    for
        lg.info(f"No {sym} MD Update. Last Updated: {md[f'{sym}_lastTS']}")

# Generate tradeFile
trades = AFBI.generateAFBITradeFile(fitModels, md, initPositions, AFBI.timezone, send=False)

# Save
modelState = utility.saveModelState(initSeeds, initPositions, md, trades, fitModels)

lg.info("Completed.")
