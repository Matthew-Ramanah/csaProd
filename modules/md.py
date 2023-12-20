from pyConfig import *


def findExch(sym):
    for exch in exchangeMap:
        if sym in exchangeMap[exch]:
            return exch
    return


def addPrefix(df, sym):
    return df.add_prefix(f'{sym}_')


def mergeOnEndTS(md, raw, sym):
    raw['mergeTS'] = raw[f'{sym}_end_ts']
    return pd.merge_asof(md, raw, on='mergeTS', direction='backward')


def loadRawData(sym):
    exch = findExch(sym)
    raw = pd.read_hdf(f"{rawDataRoot}{exch}/{sym}.h5", key=sym)
    raw = raw.set_index('end_ts', drop=False)
    raw = raw[~raw.index.duplicated(keep='first')]
    return addPrefix(raw, sym)


def loadSyntheticMD(cfg, researchFeeds, maxUpdates):
    feed = pd.DataFrame()
    for sym in cfg['predictors']:
        raw = loadRawData(sym)
        feed = pd.concat([feed, raw], axis=1)

    feed = sampleFeed(feed, researchFeeds, maxUpdates=maxUpdates)
    feed = convertToProdFormat(feed, cfg)
    lg.info(f"Synthetic Market Data Feed Loaded")
    return feed


def convertToProdFormat(md, cfg):
    for sym in cfg['predictors']:
        md[f'{sym}_midPrice'] = 0.5 * (md[f'{sym}_ask_price'] + md[f'{sym}_bid_price'])
        md[f'{sym}_lastTS'] = md[f'{sym}_end_ts']

    return md


def sampleFeed(feed, researchFeeds, maxUpdates):
    feed['end_ts'] = feed.index
    start = researchFeeds['recon'].index[0]
    end = researchFeeds['recon'].index[-1]
    feed = feed.loc[(feed['end_ts'] >= start) & (feed['end_ts'] <= end)]
    return feed.iloc[0:maxUpdates]
