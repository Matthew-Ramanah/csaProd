from pyConfig import *
from modules import pta

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

logs = pta.loadLogs(cfg)

alphasLogs = pta.loadAlphasLogs(cfg)

symsToPlot = ["ICE-US_KC0"]  # , 'ES0', 'ZW0', 'KE0', 'RS0']
pta.plotLogs(logs, symsToPlot)
lg.info("Completed.")
