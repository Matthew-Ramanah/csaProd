from pyConfig import *
from modules import dataFeed, utility, AFBI

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

# Load Seed Dump
researchFeeds = utility.loadResearchFeeds(cfg)
seeds = utility.constructSeeds(researchFeeds, cfg, prod=True)


def dumpSeeds(fitModels, md):
    # Dump latest MD

    # Dump midPrices & vols for all preds + target

    # Dump lastTS date

    # Dump last fxRate

    # Dump smooth, Z & vol for all features

    # Dump latest positions
    return


# Load Positions
positions = AFBI.detectAFBIPositions(cfg)

# Initialise models
fitModels = utility.initialiseModels(cfg, seeds=seeds, positions=positions, prod=True)

# Get latest md object
md = dataFeed.feed(cfg).pullLatestMD()

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
