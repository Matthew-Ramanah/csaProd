from pyConfig import *
from modules import pta

cfg_file = root + "models/AFBI/config/ftiRemoved.json"
with open(cfg_file, 'r') as f:
    cfg = json.load(f)

logDir = paperLogRoot  # logRoot
logs = pta.loadLogs(cfg, logDir)
alphasLogs = pta.loadAlphasLogs(cfg, logDir)

symsToPlot = cfg['targets']  # ["ICE-US_KC0"]
pta.plotLogs(logs, alphasLogs, symsToPlot)
lg.info("Completed.")
