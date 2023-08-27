from pyConfig import *
from modules import syntheticMD


def emaUpdate(lastValue, thisValue, decay, invTau):
    alpha = np.exp(invTau * decay)
    return alpha * thisValue + (1 - alpha) * lastValue


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

    def __init__(self, target, name, decay, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed, accel):
        self.target = target
        self.decay = decay
        self.name = name
        self.zInvTau = np.float64(1 / (zHL * logTwo))
        self.zVal = zSeed
        self.smoothInvTau = np.float64(1 / (smoothFactor * zHL * logTwo))
        self.smoothVal = smoothSeed
        self.lastSmoothVal = smoothSeed
        self.volInvTau = np.float64(1 / (volHL * logTwo))
        self.vol = volSeed
        self.accel = accel

    def onMdhUpdate(self):
        self.decayCalc()
        self.calcRawVal()
        self.updateSmoothVal()
        self.updateZVal()
        self.updateVolatility()
        self.updateAlphaVal()
        return

    def decayCalc(self):
        self.decay = self.target.timeDecay
        return

    def calcRawVal(self):
        return

    def updateSmoothVal(self):
        thisSmoothVal = emaUpdate(self.lastSmoothVal, self.rawVal, self.decay, self.smoothInvTau)
        if self.accel:
            self.smoothVal = thisSmoothVal - self.lastSmoothVal
        else:
            self.smoothVal = thisSmoothVal
        self.lastSmoothVal = thisSmoothVal
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


class move(alpha):
    def calcRawVal(self):
        self.rawVal = self.target.annPctChange
        return


class basis(alpha):
    def __init__(self, target, name, decay, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed, front, back):
        super().__init__(target, name, decay, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed)
        self.front = front
        self.lastFrontMid = front.midPrice
        self.back = back
        self.lastBackMid = back.midPrice

    def calcRawVal(self):
        if self.front.contractChange:
            frontDelta = 0
        else:
            frontDelta = (self.front.midPrice - self.lastFrontMid) / self.front.midPrice
        if self.back.contractChange:
            backDelta = 0
        else:
            backDelta = (self.back.midPrice - self.lastBackMid) / self.back.midPrice

        self.rawVal = frontDelta - backDelta
        self.lastFrontMid = self.front.midPrice
        self.lastBackMid = self.back.midPrice
        return


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
