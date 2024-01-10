from pyConfig import *
from modules import pta
from models.AFBI.interface import AFBI

# cfg_file = root + "models/AFBI/config/afbiRecon.json"
with open(cfg_file, 'r') as f:
    cfg = json.load(f)

logDir = logRoot  # paperLogRoot  #
logs = pta.loadLogs(cfg, logDir)
alphasLogs = pta.loadAlphasLogs(cfg, logDir)
tradeLogs = pta.loadTradeLogs(cfg, timezone=AFBI.timezone)

symsToPlot = cfg['targets']
pta.plotLogs(cfg, logs, alphasLogs, tradeLogs, symsToPlot)
lg.info("Completed.")
