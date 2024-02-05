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
        names = [f'lastTS', f'{sym}_contractChange', f'{sym}_close', f'{sym}_timeDelta', f'{sym}_Volatility',
                 f'{sym}_priceDelta', f'{sym}_CumAlpha', 'normedHoldings', f'{sym}_InitHoldings', f'{sym}_Trades',
                 f'{sym}_maxTradeSize', f'{sym}_Liquidity', f'{sym}_MaxPosition', f'{sym}_notionalPerLot',
                 f'{sym}_{fx}_DailyRate']
        logs[sym] = pd.DataFrame(rawLogs[sym], columns=names)

    for sym in logs:
        logs[sym].index = pd.to_datetime(logs[sym]['lastTS'], format='%Y_%m_%d_%H')
        logs[sym][f'{sym}_TargetPos'] = logs[sym][f'{sym}_InitHoldings'] + logs[sym][f'{sym}_Trades']

    return logs


def loadLogs(cfg, logDir):
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
    logs = formatRawLogs(logs)
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


def converListToDfALogs(alphasLogs, cfg):
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

    return alphasLogs


def formatAlphasLogs(rawAL, cfg):
    alphasLogs = convertRawToListALogs(rawAL)
    alphasLogs = removeEmptyALogs(alphasLogs)
    alphasLogs = converListToDfALogs(alphasLogs, cfg)
    return alphasLogs


def loadAlphasLogs(cfg, logDir):
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
    alphasLogs = formatAlphasLogs(rawAL, cfg)
    return alphasLogs


def findTradePriceScaler(sym):
    tradePriceMultipliers = {'ICE-US_KC0': 100, 'ICE-US_CT0': 100, 'KE0': 100, 'ZW0': 100, "LE0": 100, "ZS0": 100}
    if sym in list(tradePriceMultipliers):
        return tradePriceMultipliers[sym]
    return 1


def plotLogs(cfg, logs, alphasLogs, symsToPlot):
    for sym in symsToPlot:
        desc = utility.findDescription(sym)
        if len(logs[sym]) == 0:
            print(f"Can't plot {sym} logs as no logFiles detected")
            continue
        log = logs[sym]
        fig, axs = plt.subplots(4, sharex='all')
        fig.suptitle(f"{desc}")
        axs[0].step(log.index, log[f'{sym}_close'], label='close', where='post', color='orange')
        """
        trades = tradeLogs[sym]
        buys = trades.loc[trades['Notional Quantity'] > 0].dropna()
        sells = trades.loc[trades['Notional Quantity'] < 0].dropna()
        tpScaler = findTradePriceScaler(sym)
        axs[0].plot(buys['execTime'], buys['tradePrice'] * tpScaler, "^", color='blue', label='buy')
        axs[0].plot(sells['execTime'], sells['tradePrice'] * tpScaler, "v", color='red', label='sell')
        """
        axs[0].legend(loc='upper left')
        axs[1].step(log.index, log[f'normedHoldings'], label='normedHoldings', where='post', color='green')
        axs[1].axhline(y=0, color='black', linestyle='--')
        axs[1].legend(loc='upper left')
        for name in cfg['fitParams'][sym]['alphaWeights']:
            if name == 'kappa':
                continue
            axs[2].step(alphasLogs[sym][name].index, alphasLogs[sym][name]['weighted'], label=name, where='post')
        axs[2].step(log.index, log[f'{sym}_CumAlpha'], label='CumAlpha', where='post', color='magenta')
        axs[2].axhline(y=0, color='black', linestyle='--')
        axs[2].legend(loc='upper left')
        axs[3].step(log.index, log[f'{sym}_InitHoldings'], label='InitPos', where='post', color='orange')
        axs[3].step(log.index, log[f'{sym}_TargetPos'], label='TargetPos', where='post', color='olive')
        axs[3].axhline(y=0, color='black', linestyle='--')
        axs[3].legend(loc='upper left')
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
