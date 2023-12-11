from pyConfig import *
from modules import pta

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

logs = pta.loadLogs(cfg)

lg.info("Completed.")
