from pyConfig import *
from modules import utility


def setLogIndex(log, col):
    log.index = pd.to_datetime(log[col], format='%Y_%m_%d_%H')
    return log


def processLogs(fitModels):
    logs = {}
    for sym in fitModels:
        logs[sym] = {}
        fx = utility.findNotionalFx(sym)
        logs[sym]['model'] = pd.DataFrame(fitModels[sym].log,
                                          columns=[f'lastTS', f'{sym}_contractChange', f'{sym}_close',
                                                   f'{sym}_timeDelta', f'{sym}_Volatility', f'{sym}_priceDelta',
                                                   f'{sym}_CumAlpha', f'{sym}_Holdings', f'{sym}_InitHoldings',
                                                   f'{sym}_Trades', f'{sym}_maxTradeSize', f'{sym}_Liquidity',
                                                   f'{sym}_maxLots', f'{sym}_notionalPerLot',
                                                   f'{sym}_{fx}_DailyRate']).dropna()
        logs[sym]['model'][f'{sym}_BasketHoldings'] = logs[sym]['model'][f'{sym}_Trades'].cumsum()
        logs[sym]['model'] = setLogIndex(logs[sym]['model'], col='lastTS')

        for name in fitModels[sym].alphaDict:
            logs[sym][name] = pd.DataFrame(fitModels[sym].alphaDict[name].log,
                                           columns=['lastTS', 'decay', 'rawVal', 'smoothVal', 'zVal', 'vol',
                                                    f'feat_{name}']).dropna()
            logs[sym][name].index = logs[sym][name]['lastTS']

        for pred in fitModels[sym].predictors:
            logs[sym][pred] = pd.DataFrame(fitModels[sym].predictors[pred].log,
                                           columns=[f'{pred}_lastTS', f'{pred}_contractChange', f'{pred}_close',
                                                    f'{pred}_Volatility']).dropna()
            logs[sym][pred] = setLogIndex(logs[sym][pred], col=f'{pred}_lastTS')

    lg.info("Processed Logs.")
    return logs


def checkTolerance(research, prod, cols, ts, tol=0.02):
    for col in cols:
        if research[col] != 0:
            err = (abs(prod[col] - research[col])) / research[col]
        else:
            err = (abs(prod[col] - research[col]))
        if err > tol:
            lg.info(f'Recon Failed at {ts} for {col}. Research: {research[col]}. Prod: {prod[col]}')
    return


def constructTimeDeltas(fitModels, researchFeeds):
    """
    Reconcile the timeDeltas rather than the total decay to account for different seeding periods
    """
    # Reconcile the timeDeltas rather than the total decay to account for different seeding periods
    for sym in fitModels:
        researchFeeds['recon'][f'{sym}_timeDR_Delta'] = researchFeeds['recon'][f'{sym}_timeDR'].diff().fillna(0)
    return researchFeeds


def reconcile(prodLogs, researchFeeds, fitModels):
    for ts in researchFeeds['recon'].index:
        for sym in fitModels:
            if ts not in prodLogs[sym]['model'].index:
                continue
            modelCols = [f'{sym}_contractChange', f'{sym}_midPrice', f'Volatility_{sym}', f'{sym}_CumAlpha',
                         f'{sym}_BasketHoldings']
            checkTolerance(researchFeeds['recon'].loc[ts], prodLogs[sym]['model'].loc[ts], modelCols, ts)

            for alph in fitModels[sym].alphaList:
                ftCols = [f'feat_{alph.name}']
                checkTolerance(researchFeeds[sym].loc[ts], prodLogs[sym][alph.name].loc[ts], ftCols, ts)

    lg.info('Reconciliation Complete.')
    return


def plotReconCols(cfg, prodLogs, researchFeeds, fitModels, symsToPlot):
    for sym in symsToPlot:
        fts = cfg['fitParams'][sym]['feats']
        preds = list(fitModels[sym].predictors.keys())
        reconCols = [f'{sym}_CumAlpha', f'{sym}_BasketHoldings']
        prod = prodLogs[sym]['model']
        res = researchFeeds[sym]
        recon = researchFeeds['recon']

        fig, axs = plt.subplots(len(reconCols) + len(preds) + 1, sharex='all')
        fig.suptitle(f"{sym} Reconciliation")
        axs[0].step(res.index, res[f'{sym}_close'], label=f'Research: {sym}_close', where='post')
        axs[0].step(prod.index, prod[f'{sym}_close'], label=f'Prod: {sym}_close', where='post')
        axs[0].legend(loc='upper right')

        # Plot Model
        for i, col in enumerate(reconCols):
            axs[i + 1].step(recon.index, recon[col], label=f'Research: {col}', where='post')
            axs[i + 1].step(prod.index, prod[col], label=f'Prod: {col}', where='post')
            axs[i + 1].legend(loc='upper right')

        if False:
            # Plot Alphas
            for j, ft in enumerate(fts):
                name = ft.replace('feat_', '')
                axs[i + j + 2].step(res.index, res[ft], label=f'Research: {ft}', where='post')
                axs[i + j + 2].step(prodLogs[sym][name].index, prodLogs[sym][name][ft], label=f'Prod: {ft}',
                                    where='post')
                axs[i + j + 2].axhline(y=0, color='black', linestyle='--')
                axs[i + j + 2].legend(loc='upper right')

        for k, pred in enumerate(preds):
            axs[i + k + 2].step(res.index, res[f'{pred}_close'], label=f'Research: {pred}_close', where='post')
            axs[i + k + 2].step(prodLogs[sym][pred].index, prodLogs[sym][pred][f'{pred}_close'],
                                label=f'Prod: {pred}_close', where='post')
            axs[i + k + 2].axhline(y=0, color='black', linestyle='--')
            axs[i + k + 2].legend(loc='upper right')

        fig.show()
    return


def calcPnLs(prodLogs, researchFeeds, cfg):
    pnls = pd.DataFrame(index=researchFeeds['recon'].index)
    pnls['TradingProfit'] = np.zeros(len(pnls))
    refData = utility.loadRefData()
    for sym in prodLogs:
        log = prodLogs[sym]['model']
        trades = log[f'{sym}_Trades']
        lastHoldings = log[f'{sym}_BasketHoldings'].shift(1).fillna(0)
        mpDelta = log[f'{sym}_midPrice'].diff().fillna(0)
        fx = utility.findNotionalFx(sym)
        fxRate = log[f'{sym}_{fx}_DailyRate']
        tickScaler = float(refData['tickValue'][sym]) / float(cfg['fitParams'][sym]['tickSizes'][sym]) * fxRate
        buyCost = sellCost = float(cfg['fitParams'][sym]['tickSizes'][sym])
        uncostedPnl = np.cumsum(lastHoldings * tickScaler * mpDelta)
        tCosts = np.cumsum(
            tickScaler * np.abs(trades) * np.where(trades > 0, buyCost, np.where(trades < 0, sellCost, 0)))
        pnls[f'{sym}_TradingProfit'] = uncostedPnl - tCosts
        pnls['TradingProfit'] += pnls[f'{sym}_TradingProfit']
    return pnls.ffill().fillna(0)


def findAssClasses(cfg):
    refData = utility.loadRefData()
    assClasses = {}
    for target in cfg['targets']:
        assClass = refData.loc[target]['assetClass']
        if assClass not in assClasses:
            assClasses[assClass] = [target]
        else:
            assClasses[assClass].append(target)

    return assClasses


def plotPnLDeltas(prodLogs, researchFeeds, cfg):
    pnls = calcPnLs(prodLogs, researchFeeds, cfg)
    assClasses = findAssClasses(cfg)
    tick = mtick.StrMethodFormatter(dollarFmt)

    fig, axs = plt.subplots(len(assClasses) + 1, sharex='all')
    fig.suptitle(f"PnL Deltas")
    delta = researchFeeds['recon']['TradingProfit'] - pnls[f'TradingProfit']
    axs[0].step(delta.index, delta, label=f'Cumulative', where='post')

    for i, assClass in enumerate(assClasses):
        assetDelta = np.zeros(len(researchFeeds['recon']))
        for sym in assClasses[assClass]:
            delta = researchFeeds['recon'][f'{sym}_CostedPnl'] - pnls[f'{sym}_TradingProfit']
            axs[i + 1].step(delta.index, delta, label=f'{sym}', where='post')
            assetDelta += delta
        axs[i + 1].set_title(f'{assClass}')
        axs[i + 1].legend(loc='upper right')
        axs[i + 1].axhline(y=0, color='black', linestyle='--')
        axs[i + 1].yaxis.set_major_formatter(tick)

        axs[0].step(delta.index, assetDelta, label=f'{assClass}')

    axs[0].legend(loc='upper right')
    axs[0].axhline(y=0, color='black', linestyle='--')
    axs[0].yaxis.set_major_formatter(tick)
    fig.show()
    return


def plotPnLs(prodLogs, researchFeeds, cfg):
    pnls = calcPnLs(prodLogs, researchFeeds, cfg)
    assClasses = findAssClasses(cfg)
    tick = mtick.StrMethodFormatter(dollarFmt)

    fig, axs = plt.subplots(len(assClasses) + 1, sharex='all')
    fig.suptitle(f"PnL Reconciliation")
    axs[0].step(researchFeeds['recon'].index, researchFeeds['recon']['TradingProfit'], label=f'Research: TradingProfit',
                where='post')
    axs[0].step(pnls.index, pnls[f'TradingProfit'], label=f'Prod: TradingProfit', where='post')
    axs[0].legend(loc='upper right')
    axs[0].axhline(y=0, color='black', linestyle='--')
    axs[0].yaxis.set_major_formatter(tick)

    for i, assClass in enumerate(assClasses):
        researchPnl = np.zeros(len(researchFeeds['recon']))
        prodPnl = np.zeros(len(pnls))
        for sym in assClasses[assClass]:
            symResPnl = researchFeeds['recon'][f'{sym}_CostedPnl']
            symProdPnl = pnls[f'{sym}_TradingProfit']
            axs[i + 1].step(symResPnl.index, symResPnl, label=f'Research: {sym}_TradingProfit', where='post')
            axs[i + 1].step(pnls.index, symProdPnl, label=f'Prod: {sym}_TradingProfit', where='post')
            researchPnl += symResPnl
            prodPnl += symProdPnl
        axs[i + 1].set_title(f'{assClass}')
        axs[i + 1].legend(loc='upper right')
        axs[i + 1].axhline(y=0, color='black', linestyle='--')
        axs[i + 1].yaxis.set_major_formatter(tick)

        axs[0].step(researchFeeds['recon'].index, researchPnl, label=f'Research: {assClass}')
        axs[0].step(pnls.index, prodPnl, label=f'Prod: {assClass}')

    fig.show()
    return


def reconRVAlpha(researchFeeds, prodLogs):
    name = 'ZL0_CL0_RV_timeDR_146'
    ft = f'feat_{name}'
    sym = 'ZL0'
    pred = 'CL0'
    res = researchFeeds[sym]
    df = prodLogs[sym][name]

    fig, axs = plt.subplots(8, sharex='all')
    fig.suptitle(f"{ft} Reconciliation")
    axs[0].step(res.index, res[f'{sym}_midPrice'], label=f'Research {sym}_midPrice', where='post')
    axs[0].step(prodLogs[sym]['model'].index, prodLogs[sym]['model'][f'{sym}_midPrice'], label=f'Prod {sym}_midPrice',
                where='post')
    axs[0].legend(loc='upper right')
    axs[1].step(res.index, res[f'{pred}_midPrice'], label=f'Research {pred}_midPrice', where='post')
    axs[1].step(prodLogs[sym][pred].index, prodLogs[sym][pred][f'{pred}_midPrice'], label=f'Prod {pred}_midPrice',
                where='post')
    axs[1].legend(loc='upper right')
    axs[2].step(res.index, res[f'{pred}_timeDR_Delta'], label='Research Decay', where='post')
    axs[2].step(df.index, df['decay'], label='Prod Decay', where='post')
    axs[2].legend(loc='upper right')

    axs[3].step(res.index, res[f'{pred}_RVDelta'], label='Research rawVal', where='post')
    axs[3].step(df.index, df['rawVal'], label='Prod rawVal', where='post')
    axs[3].legend(loc='upper right')

    axs[4].step(res.index, res[f'{name}_Smooth'], label='Research smoothVal', where='post')
    axs[4].step(df.index, df['smoothVal'], label='Prod smoothVal', where='post')
    axs[4].legend(loc='upper right')
    axs[5].step(res.index, res[f'{name}_Z'], label='Research zVal', where='post')
    axs[5].step(df.index, df['zVal'], label='Prod zVal', where='post')
    axs[5].legend(loc='upper right')
    axs[6].step(res.index, res[f'{name}_Std'], label='Research vol', where='post')
    axs[6].step(df.index, df['vol'], label='Prod vol', where='post')
    axs[6].legend(loc='upper right')
    axs[7].step(res.index, res[ft], label='Research Feat', where='post')
    axs[7].step(df.index, df[ft], label='Prod Feat', where='post')
    axs[7].legend(loc='upper right')
    fig.show()
    return


def runRecon(prodFeed, fitModels, printRunTimes=False):
    runTimes = []
    for i, md in prodFeed.iterrows():
        t0 = time.time()
        for sym in fitModels:
            fitModels[sym].mdUpdate(md)

        t1 = time.time()
        runTimes.append(1000 * (t1 - t0))
    lg.info(f"Processed {len(prodFeed):,} Updates")

    if printRunTimes:
        print(
            f'Tick2Trade Mean: {round(statistics.mean(runTimes), 2)} ms. Max: {round(max(runTimes), 2)} ms. Min: {round(min(runTimes), 2)}')
    return fitModels


def initialisePositions(cfg):
    pos = {}
    for sym in cfg['targets']:
        pos[sym] = 0
    return pos
