from pyConfig import *
from modules import dataFeed, utility
from interfaces import common

# Run-time options
cfgFiles = ['qubeRecon', 'expandedRecon']

send = False
saveModels = False
saveLogs = False

cfgs = common.detectConfigs(cfgFiles)

# Initialise
initSeeds, initPositions, fitModels = common.initialiseSystems(cfgs)

# Pull Market Data
mdPipe = dataFeed.feed(cfgs)
md = mdPipe.pullLatestMD(syntheticIncrement=0)

# Update Models
fitModels = common.updateModels(fitModels, md)

# Generate Output Files
#common.generateOutputFiles(cfgs, fitModels, mdPipe, initPositions, initSeeds, md, send, save)

lg.info("Completed.")
