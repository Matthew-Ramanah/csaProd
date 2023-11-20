from pyConfig import *
from modules import dataFeed, utility

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

# Load Seed Dump
researchFeeds = utility.loadResearchFeeds(cfg)
seeds = utility.constructSeeds(researchFeeds, cfg, prod=True)


# Load Positions
def loadPositions(cfg):
    # Placeholder until I load in the email file
    positions = {}
    for sym in cfg['targets']:
        positions[sym] = 0

    return positions


positions = loadPositions(cfg)

# Initialise models
fitModels = utility.initialiseModels(cfg, seeds=seeds, positions=positions, prod=True)

# Get latest md object
md = dataFeed.feed(cfg, backMonths).pullLatestMD()

# Parse the same md through several times for now
for i in range(3):
    for sym in fitModels:
        # Update models
        fitModels[sym].mdUpdate(md)

        # Generate tradeFile

        # Dump new seeds & logs

lg.info("Completed.")
for sym in fitModels:
    print(sym)
    for j in fitModels[sym].log:
        print(j)
    print("")
