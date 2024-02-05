from pyConfig import *
from modules import pta
with open(cfg_file, 'r') as f:
    cfg = json.load(f)

logDir = logRoot  # paperLogRoot  #
logs = pta.loadLogs(cfg, logDir)
alphasLogs = pta.loadAlphasLogs(cfg, logDir)

symsToPlot = cfg['targets']
pta.plotLogs(cfg, logs, alphasLogs, symsToPlot)
lg.info("Completed.")
