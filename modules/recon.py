import numpy as np

from pyConfig import *
from modules import utility


def processLogs(fitModels):
    logs = {}
    for sym in fitModels:
        logs[sym] = {}
        logs[sym]['model'] = pd.DataFrame(fitModels[sym].log,
                                          columns=[f'lastTS', f'{sym}_contractChange', f'{sym}_bidPrice',
                                                   f'{sym}_askPrice', f'{sym}_midPrice', f'{sym}_timeDR_Delta',
                                                   f'Volatility_{sym}_timeDR', f'annPctChange_{sym}_timeDR',
                                                   f'{sym}_CumAlpha', 'hOpt', f'{sym}_BasketHoldings',
                                                   f'{sym}_Trades', f'{sym}_BuyCost', f'{sym}_SellCost']).set_index(
            'lastTS')
        for name in fitModels[sym].alphaDict:
            logs[sym][name] = pd.DataFrame(fitModels[sym].alphaDict[name].log,
                                           columns=['lastTS', 'decay', 'rawVal', 'smoothVal', 'zVal', 'vol',
                                                    f'feat_{name}']).set_index('lastTS')
        for pred in fitModels[sym].predictors:
            logs[sym][pred] = pd.DataFrame(fitModels[sym].predictors[pred].log,
                                           columns=[f'{pred}_symbol', f'{pred}_lastTS', f'{pred}_contractChange',
                                                    f'{pred}_bidPrice', f'{pred}_askPrice', f'{pred}_midPrice',
                                                    f'{pred}_timeDR_Delta',
                                                    f'annualPctChange_{pred}_timeDR']).set_index(f'{pred}_lastTS')

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
            modelCols = [f'{sym}_contractChange', f'{sym}_midPrice', f'{sym}_timeDR_Delta', f'Volatility_{sym}_timeDR',
                         f'{sym}_CumAlpha', f'{sym}_BasketHoldings']
            checkTolerance(researchFeeds['recon'].loc[ts], prodLogs[sym]['model'].loc[ts], modelCols, ts)

            for alph in fitModels[sym].alphaList:
                ftCols = [f'feat_{alph.name}']
                checkTolerance(researchFeeds[sym].loc[ts], prodLogs[sym][alph.name].loc[ts], ftCols, ts)

    lg.info('Reconciliation Complete.')
    return


def plotReconCols(cfg, prodLogs, researchFeeds, fitModels):
    for sym in fitModels:
        fts = cfg['fitParams'][sym]['feats']
        reconCols = [f'{sym}_timeDR_Delta', f'Volatility_{sym}_timeDR', f'{sym}_CumAlpha', f'{sym}_BasketHoldings',
                     f'{sym}_Trades']
        prod = prodLogs[sym]['model']

        fig, axs = plt.subplots(len(reconCols) + len(fitModels[sym].predictors) + len(fts), sharex='all')
        fig.suptitle(f"{sym} Reconciliation")
        # Plot predictors
        for i, pred in enumerate(fitModels[sym].predictors):
            axs[i].step(researchFeeds[sym].index, researchFeeds[sym][f'{pred}_midPrice'],
                        label=f'Research: {pred}_midPrice', where='post')
            axs[i].step(prodLogs[sym][pred].index, prodLogs[sym][pred][f'{pred}_midPrice'],
                        label=f'Prod: {pred}_midPrice', where='post')
            axs[i].legend(loc='upper right')
        fig.show()

        # Plot Model
        for j, col in enumerate(reconCols):
            axs[i + j + 1].step(researchFeeds['recon'].index, researchFeeds['recon'][col], label=f'Research: {col}',
                                where='post')
            axs[i + j + 1].step(prod.index, prod[col], label=f'Prod: {col}', where='post')
            axs[i + j + 1].legend(loc='upper right')

        # Plot Alphas
        for k, ft in enumerate(fts):
            name = ft.replace('feat_', '')
            axs[i + j + k + 2].step(researchFeeds[sym].index, researchFeeds[sym][ft], label=f'Research: {ft}',
                                    where='post')
            axs[i + j + k + 2].step(prodLogs[sym][name].index, prodLogs[sym][name][ft], label=f'Prod: {ft}',
                                    where='post')
            axs[i + j + k + 2].axhline(y=0, color='black', linestyle='--')
            axs[i + j + k + 2].legend(loc='upper right')
        fig.show()
    return


def calcPnLs(prodLogs, researchFeeds, cfg):
    pnls = pd.DataFrame(index=researchFeeds['recon'].index)
    pnls['TradingProfit'] = np.zeros(len(pnls))
    refData = utility.loadRefData()
    for sym in prodLogs:
        tickScaler = refData['tickValue'][sym] / float(cfg['fitParams'][sym]['tickSizes'][sym])
        log = prodLogs[sym]['model']
        trades = log[f'{sym}_Trades']
        lastHoldings = log[f'{sym}_BasketHoldings'].shift(1).fillna(0)
        mpDelta = log[f'{sym}_midPrice'].diff().fillna(0)
        uncostedPnl = np.cumsum(lastHoldings * tickScaler * mpDelta)
        tCosts = np.cumsum(tickScaler * np.abs(trades) * np.where(trades > 0, log[f'{sym}_BuyCost'],
                                                                  np.where(trades < 0,
                                                                           log[f'{sym}_SellCost'], 0)))
        fees = np.cumsum(np.abs(trades) * refData['feesPerLot'][sym])
        pnls[f'{sym}_TradingProfit'] = uncostedPnl - tCosts - fees
        pnls['TradingProfit'] += pnls[f'{sym}_TradingProfit']
    return pnls.ffill().fillna(0)


def plotPnLs(prodLogs, researchFeeds, cfg):
    pnls = calcPnLs(prodLogs, researchFeeds, cfg)
    fig, axs = plt.subplots(len(prodLogs) + 1, sharex='all')
    fig.suptitle(f"PnL Reconciliation")
    axs[0].step(researchFeeds['recon'].index, researchFeeds['recon']['TradingProfit'], label=f'Research: TradingProfit',
                where='post')
    axs[0].step(pnls.index, pnls[f'TradingProfit'], label=f'Prod: TradingProfit', where='post')
    axs[0].legend(loc='upper right')
    axs[0].axhline(y=0, color='black', linestyle='--')
    for i, sym in enumerate(prodLogs):
        researchProfit = researchFeeds['recon'][f'{sym}_CostedPnl'] - researchFeeds['recon'][f'{sym}_Fees']
        axs[i + 1].step(researchProfit.index, researchProfit, label=f'Research: {sym}_TradingProfit', where='post')
        axs[i + 1].step(pnls.index, pnls[f'{sym}_TradingProfit'], label=f'Prod: {sym}_TradingProfit', where='post')
        axs[i + 1].legend(loc='upper right')
        axs[i + 1].axhline(y=0, color='black', linestyle='--')
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
