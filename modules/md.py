from pyConfig import *
from modules import utility


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
    raw = pd.read_hdf(f"{rawDataRoot}/{sym}.h5", key=sym)
    raw = raw[~raw.index.duplicated(keep='first')]
    return addPrefix(raw, sym)


def loadSyntheticMD(cfg, researchFeeds, maxUpdates):
    feed = pd.DataFrame()
    for sym in cfg['fitParams']['basket']['symbolsNeeded']:
        raw = loadRawData(sym)
        feed = pd.concat([feed, raw], axis=1)

    feed = sampleFeed(feed, researchFeeds, maxUpdates=maxUpdates)
    lg.info(f"Synthetic Market Data Feed Loaded")
    return feed


def dropFeedTimezone(feed):
    feed.index = feed.index.tz_localize(None)
    return feed


def sampleFeed(feed, researchFeeds, maxUpdates):
    start = researchFeeds['recon'].index[0]
    end = researchFeeds['recon'].index[-1]
    feed = feed.loc[(feed.index >= start) & (feed.index <= end)]
    return feed.iloc[0:maxUpdates]
