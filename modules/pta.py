from pyConfig import *
from modules import utility


def initialiseLogDict(cfg):
    logs = {}
    for sym in cfg['targets']:
        logs[sym] = []
    return logs


def formatRawLogs(rawLogs):
    logs = {}
    for sym in rawLogs:
        fx = utility.findNotionalFx(sym)
        names = [f'lastTS', f'{sym}_contractChange', f'{sym}_midPrice', f'{sym}_timeDR_Delta', f'Volatility_{sym}',
                 f'midDelta_{sym}', f'{sym}_CumAlpha', 'hOpt', f'{sym}_InitHoldings', f'{sym}_Trades',
                 f'{sym}_maxTradeSize', f'{sym}_NormTargetHoldings', f'{sym}_MaxPosition', f'{sym}_notionalPerLot',
                 f'{sym}_{fx}_DailyRate']
        logs[sym] = pd.DataFrame(rawLogs[sym], columns=names)

    for sym in logs:
        logs[sym].index = pd.to_datetime(logs[sym]['lastTS'], format='%Y_%m_%d_%H')
        logs[sym][f'{sym}_TargetPos'] = logs[sym][f'{sym}_InitHoldings'] + logs[sym][f'{sym}_Trades']

    return logs


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


def formatAlphasLogs(rawAL):
    alphasLogs = {}
    for sym in rawAL:
        alphasLogs[sym] = {}
        for row in rawAL[sym]:
            for alpha in row:
                name = alpha[0]
                if name not in list(alphasLogs[sym].keys()):
                    alphasLogs[sym][name] = []
                alphasLogs[sym][name].append(alpha[1:])

    cols = ['timestamp', 'rawVal', 'smoothVal', 'zVal', 'vol', 'featVal', 'alphaVal']
    for sym in alphasLogs:
        for name in alphasLogs[sym]:
            alphasLogs[sym][name] = pd.DataFrame(alphasLogs[sym][name], columns=cols)
            alphasLogs[sym][name].index = pd.to_datetime(alphasLogs[sym][name]['timestamp'], format='%Y_%m_%d_%H')

    return alphasLogs


def loadAlphasLogs(cfg):
    lg.info("Loading AlphasLogs...")
    rawAL = initialiseLogDict(cfg)
    for root, dirs, files in os.walk(f'{logRoot}alphas/'):
        for file in files:
            if file.endswith(".json"):
                with open(f'{logRoot}alphas/{file}', 'r') as f:
                    rawLog = json.load(f)
                for sym in rawLog:
                    if len(rawLog[sym]) != 0:
                        rawAL[sym].append(rawLog[sym])
    alphasLogs = formatAlphasLogs(rawAL)
    return alphasLogs


def plotLogs(logs, alphasLogs, symsToPlot):
    for sym in symsToPlot:
        log = logs[sym]
        fig, axs = plt.subplots(6, sharex='all')
        fig.suptitle(f"{sym} Logs")
        axs[0].step(log.index, log[f'{sym}_midPrice'], label='midPrice', where='post', color='blue')
        axs[0].legend(loc='upper left')
        axs[1].step(log.index, log[f'Volatility_{sym}'], label='Volatility', where='post', color='red')
        axs[1].legend(loc='upper left')
        axs[2].step(log.index, log[f'{sym}_NormTargetHoldings'], label='NormHoldings', where='post', color='green')
        axs[2].axhline(y=0, color='black', linestyle='--')
        axs[2].axhline(y=-1, color='black', linestyle='--')
        axs[2].axhline(y=1, color='black', linestyle='--')
        axs[2].legend(loc='upper left')
        for name in alphasLogs[sym]:
            axs[3].step(alphasLogs[sym][name].index, alphasLogs[sym][name]['alphaVal'], label=name, where='post')
        axs[3].step(log.index, log[f'{sym}_CumAlpha'], label='CumAlpha', where='post', color='magenta')
        axs[3].axhline(y=0, color='black', linestyle='--')
        axs[3].legend(loc='upper left')
        axs[4].step(log.index, log[f'{sym}_InitHoldings'], label='InitPos', where='post', color='orange')
        axs[4].step(log.index, log[f'{sym}_TargetPos'], label='TargetPos', where='post', color='olive')
        axs[4].axhline(y=0, color='black', linestyle='--')
        axs[4].legend(loc='upper left')
        for name in alphasLogs[sym]:
            axs[5].step(alphasLogs[sym][name].index, alphasLogs[sym][name]['featVal'], label=name, where='post')
        axs[5].axhline(y=0, color='black', linestyle='--')
        axs[5].axhline(y=-signalCap, color='black', linestyle='--')
        axs[5].axhline(y=signalCap, color='black', linestyle='--')
        axs[5].legend(loc='upper left')
        fig.show()
    return
