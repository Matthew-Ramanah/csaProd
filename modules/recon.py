from pyConfig import *


def processLogs(models):
    logs = {}
    for sym in models:
        log = pd.DataFrame(models[sym].log,
                           columns=[f'lastTS', 'sym', f'{sym}_contractChange', f'{sym}_bidPrice', f'{sym}_askPrice',
                                    f'{sym}_bidSize', f'{sym}_askSize', f'{sym}_midPrice', f'{sym}_timeDR_Delta',
                                    f'Volatility_{sym}_timeDR', 'annPctChange', f'{sym}_CumAlpha', 'hOpt',
                                    f'{sym}_BasketHoldings'])
        log = log.set_index('lastTS')
        logs[sym] = log
    lg.info("Processed Logs.")
    return logs


def reconcile(prodLogs, researchFeed, models, tol=0.02):
    # Reconcile the timeDeltas rather than the total decay to account for different seeding periods
    for sym in models:
        researchFeed[f'{sym}_timeDR_Delta'] = researchFeed[f'{sym}_timeDR'].diff().fillna(0)

    laterCols = [f'{sym}_CumAlpha', f'{sym}_BasketHoldings']
    for ts in researchFeed.index:
        for sym in models:
            if ts not in prodLogs[sym].index:
                continue
            cols = [f'{sym}_contractChange', f'{sym}_bidSize', f'{sym}_askSize', f'{sym}_midPrice',
                    f'{sym}_timeDR_Delta', f'Volatility_{sym}_timeDR']
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
