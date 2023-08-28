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
    raw = pd.read_hdf(f"{data_root}raw/{exch}/{sym}.h5", key=sym)
    raw = raw.set_index('end_ts', drop=False)
    return addPrefix(raw, sym)


def loadSyntheticMD(cfg, target):
    md = loadRawData(target)
    for sym in cfg['predictors']:
        raw = loadRawData(sym)
        md = mergeOnEndTS(md, raw)
    lg.info(f"{target} Synthetic Market Data Feed Loaded")
    return md.dropna()
