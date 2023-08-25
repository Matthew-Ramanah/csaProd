from pyConfig import *
from modules import syntheticMD


class asset:
    sym = str()
    tickSize = float()
    spreadCuttoff = float()
    bid_price = float()
    bid_qty = int()
    ask_price = float()
    ask_qty = int()

    def __init__(self, sym, tickSize, spreadCutoff):
        self.sym = sym
        self.tickSize = tickSize
        self.spreadCuttoff = spreadCutoff

    def mdUpdate(self, md):
        # Data Filters
        if self.mdhSane(md):
            # MD Calcs
            self.contractChange = self.isContractChange(md)
            self.thisMid = self.midPriceCalc(md[f'{self.sym}_bid_price'], md[f'{self.sym}_ask_price'])
            self.thisMicro = self.microPriceCalc(md[f'{self.sym}_bid_price'], md[f'{self.sym}_ask_price'],
                                                 md[f'{self.sym}_bid_size'], md[f'{self.sym}_ask_size'])
            self.decayCalc(md)

            # Update Risk Model
            self.annualPctChangeCalc()

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

    def decayCalc(self, md):
        if self.contractChange:
            self.timeDecay = 0
            return

        self.timeDecay = (md[f'{self.sym}_lastTS'] - self.lastTS).seconds / aggFreq
        return

    def annualPctChangeCalc(self):
        if self.contractChange:
            self.annPctChange = 0
            return 0

        pctChange = (self.thisMid - self.midPrice) / self.thisMid
        self.annPctChange = pctChange * np.sqrt(1 / self.timeDecay)

        return


class target(asset):
    vol = float()
    volHL = int()
    alphas = []

    def __init__(self, sym, tickSize, spreadCutoff, volHL, volSeed, alphas):
        super().__init__(sym, tickSize, spreadCutoff)
        self.vol = volSeed
        self.volInvTau = np.float64(1 / (volHL * logTwo))
        self.alphas = alphas

    def updateVolatility(self):
        self.vol = np.sqrt(emaUpdate(self.vol ** 2, self.annPctChange ** 2, self.timeDecay, self.volInvTau))
        return


class alpha:
    rawVal = float()

    def __init__(self, target, name, decay, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed):
        self.target = target
        self.decay = decay
        self.name = name
        self.zInvTau = np.float64(1 / (zHL * logTwo))
        self.zVal = zSeed
        self.smoothInvTau = np.float64(1 / (smoothFactor * zHL * logTwo))
        self.smoothVal = smoothSeed
        self.volInvTau = np.float64(1 / (volHL * logTwo))
        self.vol = volSeed

    def onMdhUpdate(self, md):
        self.decayCalc(md)
        self.calcRawVal(md)
        self.updateSmoothVal()
        self.updateZVal()
        self.updateVolatility()
        self.updateAlphaVal()
        return

    def decayCalc(self, md):
        return

    def calcRawVal(self, md):
        return

    def updateSmoothVal(self):
        self.smoothVal = emaUpdate(self.smoothVal, self.rawVal, self.decay, self.smoothInvTau)
        return

    def updateZVal(self):
        self.zVal = emaUpdate(self.zVal, self.smoothVal, self.decay, self.zInvTau)
        return

    def updateVolatility(self):
        self.vol = np.sqrt(emaUpdate(self.vol ** 2, self.zVal ** 2, self.decay, self.volInvTau))
        return

    def updateAlphaVal(self):
        self.alphaVal = np.clip(self.zVal / self.vol, -signalCap, signalCap)
        return


def emaUpdate(lastValue, thisValue, decay, invTau):
    alpha = np.exp(invTau * decay)
    return alpha * thisValue + (1 - alpha) * lastValue


ZL0 = target(sym='ZL0', tickSize=0.01, spreadCutoff=0.14)
ZC0 = asset(sym='ZC0', tickSize=0.25, spreadCutoff=0.5)
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
