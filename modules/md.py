from pyConfig import *


def findExch(sym):
    for exch in exchangeMap:
        if sym in exchangeMap[exch]:
            return exch
    return


def addPrefix(df, sym):
    return df.add_prefix(f'{sym}_')


def mergeOnEndTS(md, raw):
    return pd.merge_asof(md, raw, on='end_ts', direction='backward')


def loadRawData(sym):
    exch = findExch(sym)
    raw = pd.read_hdf(f"{rawDataRoot}{exch}/{sym}.h5", key=sym)
    raw = raw.set_index('end_ts', drop=False)
    return addPrefix(raw, sym)


def loadSyntheticMD(cfg, init=False):
    md = pd.DataFrame()
    for sym in cfg['predictors']:
        raw = loadRawData(sym)
        if init:
            md = mergeOnEndTS(md, raw)
        else:
            md = raw
            init = True
    lg.info(f"Synthetic Market Data Feed Loaded")
    return md


def sampleFeed(feed, researchFeeds, maxUpdates):
    start = researchFeeds['recon'].index[0]
    end = researchFeeds['recon'].index[-1]
    feed = feed.loc[(feed['end_ts'] >= start) & (feed['end_ts'] <= end)]
    return feed.iloc[0:maxUpdates]
