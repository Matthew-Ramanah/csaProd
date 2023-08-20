from pyConfig import *
from modules import syntheticMD

target = 'ZL0'
predictors = ['ZL1']
exch = 'cme_refinitiv_v4'
decays = ['timeDR', 'microDR']
aggFreq = 60


class asset:
    sym = str()
    tickSize = float()
    spreadCuttoff = float()
    bid_price = float()
    bid_qty = int()
    ask_price = float()
    ask_qty = int()

    def __init__(self, sym, tickSize, spreadCutoff, microScaler):
        self.sym = sym
        self.tickSize = tickSize
        self.spreadCuttoff = spreadCutoff
        self.microScaler = microScaler

    def mdUpdate(self, md):
        # Data Filters
        if self.mdhSane(md):

            # MD Calcs
            self.contractChange = self.isContractChange(md)
            self.thisMid = self.midPriceCalc(md[f'{self.sym}_bid_price'], md[f'{self.sym}_ask_price'])
            self.thisMicro = self.microPriceCalc(md[f'{self.sym}_bid_price'], md[f'{self.sym}_ask_price'],
                                                 md[f'{self.sym}_bid_size'], md[f'{self.sym}_ask_size'])

            # Update Risk Model
            self.annualPctChange = self.annualPctChangeCalc()
            self.volatility = self.updateVolatility()

            # Update contract state
            self.bidPrice = md[f'{self.sym}_bid_price']
            self.askPrice = md[f'{self.sym}_ask_price']
            self.bidSize = md[f'{self.sym}_bid_size']
            self.askSize = md[f'{self.sym}_ask_size']
            self.midPrice = self.thisMid
            self.microPrice = self.thisMicro
            self.lastTS = md[f'{self.sym}_end_ts']
            self.symbol = md[f'{self.sym}_symbol']

        return

    def mdhSane(self, md):
        """
        DataFilters
        """
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

    @staticmethod
    def midPriceCalc(bidPrice, askPrice):
        return 0.5 * (bidPrice + askPrice)

    @staticmethod
    def microPriceCalc(bidPrice, askPrice, bidSize, askSize):
        sum_qty = (bidSize + askSize)
        if sum_qty != 0:
            return ((bidSize * askPrice) + (askSize * bidPrice)) / sum_qty
        return 0

    def isContractChange(self, md):
        if md[f'{self.sym}_symbol'] != self.symbol:
            return True
        return False

    def decayCalcs(self, md):
        if self.contractChange:
            self.timeDecay = 0
            self.microDecay = 0
            return

        self.timeDecay = (md[f'{self.sym}_lastTS'] - self.lastTS).seconds / aggFreq
        self.microDecay = abs(self.thisMicro - self.microPrice) / self.tickSize
        return

    def annualPctChangeCalc(self):
        if self.contractChange:
            self.annPctChangeMicro = 0
            self.annPctChangeTime = 0
            return 0

        pctChange = (self.thisMid - self.midPrice) / self.thisMid
        self.annPctChangeMicro = pctChange * np.sqrt(self.microScaler / self.microDecay)
        self.annPctChangeTime = pctChange * np.sqrt(1 / self.timeDecay)

        return

    def updateVolatility(self, md):

        return


ZL0 = asset(sym='ZL0', tickSize=0.01, spreadCutoff=0.14, microScaler=0.85)
ZC0 = asset(sym='ZC0', tickSize=0.25, spreadCutoff=0.5, microScaler=0.28)
assets = [ZL0, ZC0]

# Replace this with the live feed in production
all = syntheticMD.loadSyntheticMD(target, predictors)
feed = all.head(50)

for i, md in feed.iterrows():
    for a in assets:
        a.mdUpdate(md)

# Update contracts

# Calc Decays for each pred

# Calculate vol

# Calculate features

# Generate holdings

# Generate trades

# Log
lg.info("Completed")
