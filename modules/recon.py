from pyConfig import *


def processLogs(fitModels):
    logs = {}
    for sym in fitModels:
        log = pd.DataFrame(fitModels[sym].log,
                           columns=[f'lastTS', f'{sym}_contractChange', f'{sym}_bidPrice', f'{sym}_askPrice',
                                    f'{sym}_midPrice', f'{sym}_timeDR_Delta', f'Volatility_{sym}_timeDR',
                                    'annPctChange', f'{sym}_CumAlpha', 'hOpt', f'{sym}_BasketHoldings'])
        log = log.set_index('lastTS')
        logs[sym] = log
    lg.info("Processed Logs.")
    return logs


def reconcile(prodLogs, researchFeed, fitModels, tol=0.02):
    # Reconcile the timeDeltas rather than the total decay to account for different seeding periods
    for sym in fitModels:
        researchFeed[f'{sym}_timeDR_Delta'] = researchFeed[f'{sym}_timeDR'].diff().fillna(0)

    laterCols = [f'{sym}_CumAlpha', f'{sym}_BasketHoldings']
    for ts in researchFeed.index:
        for sym in fitModels:
            if ts not in prodLogs[sym].index:
                continue
            cols = [f'{sym}_contractChange', f'{sym}_midPrice', f'{sym}_timeDR_Delta', f'Volatility_{sym}_timeDR']
            research = researchFeed.loc[ts]
            prod = prodLogs[sym].loc[ts]
            for col in cols:
                if research[col] != 0:
                    err = (abs(prod[col] - research[col])) / research[col]
                else:
                    err = (abs(prod[col] - research[col]))
                if err > tol:
                    lg.info(f'Recon Failed at {ts} for {col}. Research: {research[col]}. Prod: {prod[col]}')
    lg.info('Reconciliation Complete.')
    return


def plotReconCols(prodLogs, researchFeed, fitModels):
    for sym in fitModels:
        cols = [f'{sym}_midPrice', f'{sym}_timeDR_Delta', f'Volatility_{sym}_timeDR', f'{sym}_contractChange', ]
        log = prodLogs[sym]

        fig, axs = plt.subplots(len(cols), sharex='all')
        fig.suptitle(f"{sym} Reconciliation")
        for i, col in enumerate(cols):
            axs[i].step(researchFeed.index, researchFeed[col], label=f'Research: {col}', where='post')
            axs[i].step(log.index, log[col], label=f'Prod: {col}', where='post')
            axs[i].legend(loc='upper left')
        fig.show()
    return
