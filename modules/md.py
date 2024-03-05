from pyConfig import *
from modules import utility


def addPrefix(df, sym):
    return df.add_prefix(f'{sym}_')


def mergeOnEndTS(feed, raw):
    """
    Drops ticks in feed before raw has valid values
    """
    return pd.merge_asof(feed, raw, on='lastTS', direction='backward').dropna()


def loadRawData(sym, cfg):
    raw = pd.read_hdf(f"{rawDataRoot}{cfg['dataTag']}/{sym}.h5", key=sym)
    raw = raw[~raw.index.duplicated(keep='first')]
    return addPrefix(raw, sym)


def loadSyntheticMD(cfg, researchFeeds, maxUpdates):
    feed = pd.DataFrame()
    for sym in cfg['fitParams']['basket']['symbolsNeeded']:
        raw = loadRawData(sym, cfg)
        if len(feed) != 0:
            feed = mergeOnEndTS(feed, raw)
        else:
            feed = raw

    feed = sampleFeed(feed, researchFeeds, maxUpdates=maxUpdates)
    feed = syntheticTimeSig(feed)
    lg.info(f"Synthetic Market Data Feed Loaded")
    return feed


def syntheticTimeSig(feed):
    feed['timeSig'] = feed.index.strftime('%Y_%m_%d_%H')
    return feed


def dropFeedTimezone(feed):
    feed.index = feed.index.tz_localize(None)
    return feed


def sampleFeed(feed, researchFeeds, maxUpdates):
    feed = feed.set_index('lastTS', drop=True)
    start = researchFeeds['recon'].index[0]
    end = researchFeeds['recon'].index[-1]
    feed = feed.loc[(feed.index >= start) & (feed.index <= end)]
    return feed.iloc[0:maxUpdates]
