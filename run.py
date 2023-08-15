from pyConfig import *
from modules import syntheticMD
from modules import dataFilters

target = 'ZL0'
predictors = ['ZL1']
exch = 'cme_refinitiv_v4'


class asset:
    def __init__(self, sym, tickSize, spreadCutoff):
        self.sym = sym
        self.tickSize = tickSize
        self.spreadCuttoff = spreadCutoff

    def mdUpdate(self, md):
        if self.mdhSane(md):
            self.bidPrice = md[f'{self.sym}_bid_price']
            self.askPrice = md[f'{self.sym}_ask_price']
            self.bidSize = md[f'{self.sym}_bid_size']
            self.askSize = md[f'{self.sym}_ask_size']
            self.lastTS = md[f'{self.sym}_end_ts']
            self.symbol = md[f'{self.sym}_symbol']

    def mdhSane(self, md):
        if md[f'{self.sym}_bid_price'] >= md[f'{self.sym}_ask_price']:
            return False
        if (md[f'{self.sym}_bid_size'] == 0) | (md[f'{self.sym}_ask_size'] == 0):
            return False
        if (md[f'{self.sym}_bid_price'] == 0) | (md[f'{self.sym}_ask_price'] == 0):
            return False
        if math.isnan(md[f'{self.sym}_bid_price']) | math.isnan(md[f'{self.sym}_ask_price']):
            return False
        if (md[f'{self.sym}_ask_price'] - md[f'{self.sym}_bid_price']) > self.spreadCuttoff:
            return False
        return True




# Replace this with the live feed in production
all = syntheticMD.loadSyntheticMD(target, predictors)
feed = all.head(5)

for i, md in feed.iterrows():
    # Data Filters
    if not dataFilters.isSane(md):
        continue

# Calc Decays for each pred

# Calculate vol

# Calculate features

# Generate holdings

# Generate trades

# Log
