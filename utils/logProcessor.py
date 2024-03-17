from pyConfig import *
from modules import pta

cfg_file = root + "config/afbiRecon.json"
with open(cfg_file, 'r') as f:
    cfg = json.load(f)

logs = pta.loadLogs(cfg)
alphasLogs = pta.loadAlphasLogs(cfg)

symsToPlot = ["@LE#"] + cfg['targets'][0:2]
pta.plotLogs(cfg, logs, alphasLogs, symsToPlot)
lg.info("Completed.")
