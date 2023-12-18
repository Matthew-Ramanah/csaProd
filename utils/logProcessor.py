from pyConfig import *
from modules import pta

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

logs = pta.loadLogs(cfg)
alphasLogs = pta.loadAlphasLogs(cfg)

symsToPlot = ["RS0"]  # , 'ES0', 'ZW0', 'KE0', 'RS0']
pta.plotLogs(logs, alphasLogs, symsToPlot)
lg.info("Completed.")
