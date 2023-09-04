from pyConfig import *


def processLogs(fitModels):
    logs = {}
    for sym in fitModels:
        logs[sym] = {}
        logs[sym]['model'] = pd.DataFrame(fitModels[sym].log,
                                          columns=[f'lastTS', f'{sym}_contractChange', f'{sym}_bidPrice',
                                                   f'{sym}_askPrice', f'{sym}_midPrice', f'{sym}_timeDR_Delta',
                                                   f'Volatility_{sym}_timeDR', 'annPctChange', f'{sym}_CumAlpha',
                                                   'hOpt', f'{sym}_BasketHoldings']).set_index('lastTS')
        for alph in fitModels[sym].alphaList:
            logs[sym][alph.name] = pd.DataFrame(alph.log, columns=['lastTS', 'rawVal', 'smoothVal', 'zVal', 'vol',
                                                                   f'feat_{alph.name}']).set_index('lastTS')
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
            modelCols = [f'{sym}_contractChange', f'{sym}_midPrice', f'{sym}_timeDR_Delta', f'Volatility_{sym}_timeDR']
            # laterCols = [f'{sym}_CumAlpha', f'{sym}_BasketHoldings']
            checkTolerance(researchFeeds['recon'].loc[ts], prodLogs[sym]['model'].loc[ts], modelCols, ts)

            for alph in fitModels[sym].alphaList:
                ftCols = [f'feat_{alph.name}']
                checkTolerance(researchFeeds[sym].loc[ts], prodLogs[sym][alph.name].loc[ts], ftCols, ts)

    lg.info('Reconciliation Complete.')
    return


def plotReconCols(cfg, prodLogs, researchFeeds, fitModels):
    for sym in fitModels:
        fts = cfg['fitParams'][sym]['feats']
        modelCols = [f'{sym}_contractChange', f'{sym}_midPrice', f'{sym}_timeDR_Delta', f'Volatility_{sym}_timeDR']
        prod = prodLogs[sym]['model']

        fig, axs = plt.subplots(len(modelCols) + len(fts), sharex='all')
        fig.suptitle(f"{sym} Reconciliation")
        for i, col in enumerate(modelCols):
            axs[i].step(researchFeeds['recon'].index, researchFeeds['recon'][col], label=f'Research: {col}',
                        where='post')
            axs[i].step(prod.index, prod[col], label=f'Prod: {col}', where='post')
            axs[i].legend(loc='upper left')
        for j, ft in enumerate(fts):
            name = ft.replace('feat_', '')
            axs[i + j + 1].step(researchFeeds[sym].index, researchFeeds[sym][ft], label=f'Research: {ft}', where='post')
            axs[i + j + 1].step(prodLogs[sym][name].index, prodLogs[sym][name][ft], label=f'Prod: {ft}', where='post')
            axs[i + j + 1].legend(loc='upper left')
        fig.show()
    return
