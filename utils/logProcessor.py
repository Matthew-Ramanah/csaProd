from pyConfig import *
from modules import pta

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

logs = pta.loadLogs(cfg)
logs = pta.formatLogs(logs)

symsToPlot = ['ZW0', "ICE-US_CT0", "FTI0", "ALSI0", "FSMI0"]
pta.plotLogs(logs, symsToPlot)
lg.info("Completed.")
