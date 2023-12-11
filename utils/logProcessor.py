from pyConfig import *
from modules import pta

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

logs = pta.loadLogs(cfg)

lg.info("Completed.")

for sym in logs:
    logs[sym].index = pd.to_datetime(logs[sym]['lastTS'], format='%Y_%m_%d_%H')

sym = 'ZW0'
log = logs[sym]

if False:
    fig, axs = plt.subplots(2, sharex='all')
    fig.suptitle(f"{sym} Logs")
    axs[0].step(log.index, log[f'{sym}_midPrice'], label='midPrice', where='post')
    axs[1].step(log.index, log[f'{sym}_NormTargetHoldings'], label='Normed Holdings', where='post')
    fig.legend()
    fig.show()
