from pyConfig import *
from modules import pta
from models.AFBI.interface import AFBI

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

logDir = logRoot  # paperLogRoot  #
logs = pta.loadLogs(cfg, logDir, AFBI.timezone)
alphasLogs = pta.loadAlphasLogs(cfg, logDir, AFBI.timezone)
tradeLogs = pta.loadTradeLogs(cfg, timezone=AFBI.timezone)

symsToPlot = ["ICE-US_CT0", "AP0"]  # cfg['targets']
pta.plotLogs(cfg, logs, alphasLogs, tradeLogs, symsToPlot)
lg.info("Completed.")
