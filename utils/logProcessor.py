from pyConfig import *
from modules import pta

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

logs = pta.loadLogs(cfg)
alphasLogs = pta.loadAlphasLogs(cfg)

symsToPlot = ["ICE-US_KC0", "RS0", "AP0", "ALSI0", "ICE-US_CT0", "KE0"]
pta.plotLogs(logs, alphasLogs, symsToPlot)
lg.info("Completed.")
