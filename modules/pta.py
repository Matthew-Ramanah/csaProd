from pyConfig import *
from modules import utility


def initialiseLogDict(cfg):
    logs = {}
    for sym in cfg['targets']:
        logs[sym] = []
    return logs


def formatRawLogs(rawLogs, timezone):
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
        logs[sym].index = logs[sym].index.tz_localize(timezone)
        logs[sym][f'{sym}_TargetPos'] = logs[sym][f'{sym}_InitHoldings'] + logs[sym][f'{sym}_Trades']

    return logs


def loadLogs(cfg, logDir, timezone):
    lg.info("Loading Logs...")
    logs = initialiseLogDict(cfg)
    for root, dirs, files in os.walk(f'{logDir}models/'):
        for file in files:
            if file.endswith(".json"):
                with open(f'{logDir}models/{file}', 'r') as f:
                    rawLog = json.load(f)
                for sym in cfg['targets']:
                    if len(rawLog[sym]) != 0:
                        logs[sym].append(rawLog[sym])
    logs = formatRawLogs(logs, timezone)
    return logs


def convertRawToListALogs(rawAL):
    alphasLogs = {}
    for sym in rawAL:
        alphasLogs[sym] = {}
        for row in rawAL[sym]:
            for alpha in row:
                if len(alpha) == 0:
                    continue
                name = alpha[0]
                if name not in list(alphasLogs[sym].keys()):
                    alphasLogs[sym][name] = []
                alphasLogs[sym][name].append(alpha[1:])

    return alphasLogs


def removeEmptyALogs(alphasLogs):
    toDelete = []
    for sym in alphasLogs:
        if len(alphasLogs[sym]) == 0:
            toDelete.append(sym)
    for i in toDelete:
        del alphasLogs[i]
    return alphasLogs


def converListToDfALogs(alphasLogs, cfg, timezone):
    cols = ['timestamp', 'rawVal', 'smoothVal', 'zVal', 'vol', 'featVal', 'alphaVal']
    for sym in alphasLogs:
        for name in cfg['fitParams'][sym]['alphaWeights']:
            if name == 'kappa':
                continue
            alphasLogs[sym][name] = pd.DataFrame(alphasLogs[sym][name], columns=cols)
            alphasLogs[sym][name]['weighted'] = alphasLogs[sym][name]['alphaVal'] * \
                                                cfg['fitParams'][sym]['alphaWeights'][name]
            alphasLogs[sym][name].index = pd.to_datetime(alphasLogs[sym][name]['timestamp'],
                                                         format='%Y_%m_%d_%H')
            alphasLogs[sym][name].index = alphasLogs[sym][name].index.tz_localize(timezone)

    return alphasLogs


def formatAlphasLogs(rawAL, cfg, timezone):
    alphasLogs = convertRawToListALogs(rawAL)
    alphasLogs = removeEmptyALogs(alphasLogs)
    alphasLogs = converListToDfALogs(alphasLogs, cfg, timezone)
    return alphasLogs


def loadAlphasLogs(cfg, logDir, timezone):
    lg.info("Loading AlphasLogs...")
    rawAL = initialiseLogDict(cfg)
    for root, dirs, files in os.walk(f'{logDir}alphas/'):
        for file in files:
            if file.endswith(".json"):
                with open(f'{logDir}alphas/{file}', 'r') as f:
                    rawLog = json.load(f)
                for sym in cfg['targets']:
                    if len(rawLog[sym]) != 0:
                        rawAL[sym].append(rawLog[sym])
    alphasLogs = formatAlphasLogs(rawAL, cfg, timezone)
    return alphasLogs


def findTradePriceScaler(sym):
    tradePriceMultipliers = {'ICE-US_KC0': 100, 'ICE-US_CT0': 100, 'KE0': 100, 'ZW0': 100, "LE0": 100, "ZS0": 100}
    if sym in list(tradePriceMultipliers):
        return tradePriceMultipliers[sym]
    return 1


def plotLogs(cfg, logs, alphasLogs, tradeLogs, symsToPlot):
    for sym in symsToPlot:
        if len(logs[sym]) == 0:
            print(f"Can't plot {sym} logs as no logFiles detected")
            continue
        log = logs[sym]
        fig, axs = plt.subplots(6, sharex='all')
        fig.suptitle(f"{sym} Logs")
        axs[0].step(log.index, log[f'{sym}_midPrice'], label='midPrice', where='post', color='orange')
        if len(tradeLogs) != 0:
            trades = tradeLogs[sym]
            buys = trades.loc[trades['Notional Quantity'] > 0].dropna()
            sells = trades.loc[trades['Notional Quantity'] < 0].dropna()
            tpScaler = findTradePriceScaler(sym)
            axs[0].plot(buys['execTime'], buys['tradePrice'] * tpScaler, "^", color='blue', label='buy')
            axs[0].plot(sells['execTime'], sells['tradePrice'] * tpScaler, "v", color='red', label='sell')
        axs[0].legend(loc='upper left')
        axs[1].step(log.index, log[f'Volatility_{sym}'], label='Volatility', where='post', color='red')
        axs[1].legend(loc='upper left')
        axs[2].step(log.index, log[f'{sym}_NormTargetHoldings'], label='NormHoldings', where='post', color='green')
        axs[2].axhline(y=0, color='black', linestyle='--')
        axs[2].axhline(y=-1, color='black', linestyle='--')
        axs[2].axhline(y=1, color='black', linestyle='--')
        axs[2].legend(loc='upper left')
        for name in cfg['fitParams'][sym]['alphaWeights']:
            if name == 'kappa':
                continue
            axs[3].step(alphasLogs[sym][name].index, alphasLogs[sym][name]['weighted'], label=name, where='post')
        axs[3].step(log.index, log[f'{sym}_CumAlpha'], label='CumAlpha', where='post', color='magenta')
        axs[3].axhline(y=0, color='black', linestyle='--')
        axs[3].legend(loc='upper left')
        axs[4].step(log.index, log[f'{sym}_InitHoldings'], label='InitPos', where='post', color='orange')
        axs[4].step(log.index, log[f'{sym}_TargetPos'], label='TargetPos', where='post', color='olive')
        axs[4].axhline(y=0, color='black', linestyle='--')
        axs[4].legend(loc='upper left')
        for name in cfg['fitParams'][sym]['alphaWeights']:
            if name == 'kappa':
                continue
            axs[5].step(alphasLogs[sym][name].index, alphasLogs[sym][name]['featVal'], label=name, where='post')
        axs[5].axhline(y=0, color='black', linestyle='--')
        axs[5].axhline(y=-signalCap, color='black', linestyle='--')
        axs[5].axhline(y=signalCap, color='black', linestyle='--')
        axs[5].legend(loc='upper left')
        fig.show()
    return


def constructExecTime(symTradeLog, timezone):
    if len(symTradeLog) == 0:
        symTradeLog['execTime'] = pd.Series()
    else:
        symTradeLog['execTime'] = (
            [parser.parse(x, tzinfos={"AWST": 8 * 3600}) for x in symTradeLog['Trade Modify Date']])
        symTradeLog['execTime'] = symTradeLog['execTime'].dt.tz_convert(timezone)
    return symTradeLog


def constructTradePrice(symTradeLog):
    fx = ''
    if len(symTradeLog) == 0:
        symTradeLog['tradePrice'] = np.nan
    else:
        try:
            float(symTradeLog['Trade Price'].iloc[0])
        except:
            if not ',' in symTradeLog['Trade Price'].iloc[0]:
                fx = symTradeLog['Trade Price'].iloc[0][:3]

        try:
            symTradeLog['tradePrice'] = [float(x.replace(fx, '')) for x in symTradeLog['Trade Price']]
        except:
            if ',' in symTradeLog['Trade Price'].iloc[0]:
                symTradeLog['tradePrice'] = [locale.atof(x) for x in symTradeLog['Trade Price']]
            else:
                symTradeLog['tradePrice'] = np.nan
    symTradeLog['fx'] = fx
    return symTradeLog


def loadTradeLogs(cfg, timezone):
    refData = utility.loadRefData()
    rawTrades = pd.read_csv(f'{tradeBlotterRoot}lastTradeBlotter.csv').dropna()
    tradeLogs = {}
    for sym in cfg['targets']:
        id = refData.loc[sym]['description']
        tradeLogs[sym] = rawTrades[[id in e for e in rawTrades['Description']]]
        tradeLogs[sym]['Currency'] = tradeLogs[sym]['Trade Price']
        tradeLogs[sym] = constructExecTime(tradeLogs[sym], timezone)
        tradeLogs[sym] = constructTradePrice(tradeLogs[sym])

    return tradeLogs
