from pyConfig import *
from modules import dataFeed, utility
from models.AFBI.interface import AFBI

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

with open(f'{interfaceRoot}modelState.json', 'r') as f:
    oldModelState = json.load(f)

# Load Seed Dump
initSeeds = oldModelState['seedDump']

# Load Positions
initPositions = AFBI.detectAFBIPositions(cfg)

# Initialise models
fitModels = utility.initialiseModels(cfg, seeds=initSeeds, positions=initPositions, prod=True)

# Pull Market Data
md = dataFeed.feed(cfg).pullLatestMD()

# Update Models
for sym in fitModels:
    fitModels[sym].mdUpdate(md)

# Generate tradeFile
trades = AFBI.generateAFBITradeFile(fitModels, md, initPositions)

# Save
modelState = utility.saveModelState(initSeeds, initPositions, md, trades, fitModels)

for sym in fitModels:
    print(f"{sym} Initial Position: {modelState['initPositions'][sym]} Traded: {modelState['trades'][sym]} Lots")

lg.info("Completed.")
