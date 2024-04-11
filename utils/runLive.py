from pyConfig import *
from modules import dataFeed
from interfaces import common

lg.info("")

# Run-time options
cfgFiles = ["afbiRecon", "qubeRecon"]

send = False
save = False

cfgs = common.detectConfigs(cfgFiles)

# Initialise
initSeeds, initPositions, fitModels, cfgs = common.initialiseSystems(cfgs)

# Pull Market Data
mdPipe = dataFeed.feed(cfgs)
md = mdPipe.pullLatestMD(syntheticIncrement=0)

# Update Models
fitModels = common.updateModels(fitModels, md)

# Generate Output Files
trades, execMD = common.generateOutputFiles(cfgs, fitModels, mdPipe, initPositions, initSeeds, md, send, save)

lg.info("Completed.")
