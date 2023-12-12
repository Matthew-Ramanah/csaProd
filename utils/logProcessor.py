from pyConfig import *
from modules import pta

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

logs = pta.loadLogs(cfg)
logs = pta.formatLogs(logs)

symsToPlot = ['ZM0', "ZS0", "CL0", "ZN0", "ZF0", "AP0"]
pta.plotLogs(logs, symsToPlot)
lg.info("Completed.")
