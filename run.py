from pyConfig import *
from modules import syntheticMD, alphas, assets




ZL0 = assets.traded(sym='ZL0', tickSize=0.01, spreadCutoff=0.14)
ZC0 = assets.asset(sym='ZC0', tickSize=0.25, spreadCutoff=0.5)
preds = [ZL0]

exch = 'cme_refinitiv_v4'
aggFreq = 60

# Replace this with the live feed in production
all = syntheticMD.loadSyntheticMD(ZL0, preds)
feed = all.head(50)

for i, md in feed.iterrows():
    for a in preds:
        a.mdUpdate(md)

# Call onMDHUpdate for all contracts (targets + assets)

# Update target volatilities

# Update target alphas

# Generate holdings

# Generate trades

# Log
lg.info("Completed")
