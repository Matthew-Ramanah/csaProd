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
    return addPrefix(raw, sym)


def loadSyntheticMD(cfg):
    ts = pd.Timestamp('2023-01-27 09:50:00+1100', tz='Australia/Sydney')
    md = pd.DataFrame()
    for sym in cfg['predictors']:
        raw = loadRawData(sym)
        md = pd.concat([md, raw], axis=1)
    lg.info(f"Synthetic Market Data Feed Loaded")
    return md


def sampleFeed(feed, researchFeeds, maxUpdates):
    feed['end_ts'] = feed.index
    start = researchFeeds['recon'].index[0]
    end = researchFeeds['recon'].index[-1]
    feed = feed.loc[(feed['end_ts'] >= start) & (feed['end_ts'] <= end)]
    return feed.iloc[0:maxUpdates]
