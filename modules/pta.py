from pyConfig import *
from modules import utility


def initialiseLogDict(cfg):
    logs = {}
    for sym in cfg['targets']:
        logs[sym] = []
    return logs


def formatRawLogs(rawLogs):
    for sym in rawLogs:
        fx = utility.findNotionalFx(sym)
        names = [f'lastTS', f'{sym}_contractChange', f'{sym}_midPrice', f'{sym}_timeDR_Delta', f'Volatility_{sym}',
                 f'midDelta_{sym}', f'{sym}_CumAlpha', 'hOpt', f'{sym}_InitHoldings', f'{sym}_Trades',
                 f'{sym}_maxTradeSize', f'{sym}_NormTargetHoldings', f'{sym}_MaxPosition', f'{sym}_notionalPerLot',
                 f'{sym}_{fx}_DailyRate']
        rawLogs[sym] = pd.DataFrame(rawLogs[sym][:-1], columns=names)

    return rawLogs


def loadLogs(cfg):
    lg.info("Loading Logs...")
    logs = initialiseLogDict(cfg)
    for root, dirs, files in os.walk(f'{logRoot}models/'):
        for file in files:
            if file.endswith(".json"):
                with open(f'{logRoot}models/{file}', 'r') as f:
                    rawLog = json.load(f)
                for sym in rawLog:
                    if len(rawLog[sym]) != 0:
                        logs[sym].append(rawLog[sym])
    logs = formatRawLogs(logs)
    return logs


def formatLogs(logs):
    for sym in logs:
        logs[sym].index = pd.to_datetime(logs[sym]['lastTS'], format='%Y_%m_%d_%H')
        logs[sym][f'{sym}_TargetPos'] = logs[sym][f'{sym}_InitHoldings'] + logs[sym][f'{sym}_Trades']
    return logs


def plotLogs(logs, symsToPlot):
    for sym in symsToPlot:
        log = logs[sym]
        fig, axs = plt.subplots(5, sharex='all')
        fig.suptitle(f"{sym} Logs")
        axs[0].step(log.index, log[f'{sym}_midPrice'], label='midPrice', where='post', color='blue')
        axs[0].legend(loc='upper left')
        axs[1].step(log.index, log[f'Volatility_{sym}'], label='Volatility', where='post', color='red')
        axs[1].legend(loc='upper left')
        axs[2].step(log.index, log[f'{sym}_CumAlpha'], label='CumAlpha', where='post', color='magenta')
        axs[2].axhline(y=0, color='black', linestyle='--')
        axs[2].legend(loc='upper left')
        axs[3].step(log.index, log[f'{sym}_NormTargetHoldings'], label='NormHoldings', where='post', color='green')
        axs[3].axhline(y=0, color='black', linestyle='--')
        axs[3].axhline(y=-1, color='black', linestyle='--')
        axs[3].axhline(y=1, color='black', linestyle='--')
        axs[3].legend(loc='upper left')
        axs[4].step(log.index, log[f'{sym}_InitHoldings'], label='InitPos', where='post', color='orange')
        axs[4].step(log.index, log[f'{sym}_TargetPos'], label='TargetPos', where='post', color='olive')
        axs[4].axhline(y=0, color='black', linestyle='--')
        axs[4].legend(loc='upper left')
        fig.show()
    return
