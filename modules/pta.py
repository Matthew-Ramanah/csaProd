import pandas as pd

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
        rawLogs[sym] = pd.DataFrame(rawLogs[sym], columns=names)
    return rawLogs


with open(cfg_file, 'r') as f:
    cfg = json.load(f)


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
