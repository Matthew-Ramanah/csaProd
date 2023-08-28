from pyConfig import *
import utility


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


class traded(asset):
    vol = float()
    volHL = int()
    alphas = []
    holdings = int()
    predictors = {}
    alphaWeights = {}

    def __init__(self, sym, tickSize, spreadCutoff, predictors, volHL, volSeed, initHoldings, alphaWeights, alphas):
        super().__init__(sym, tickSize, spreadCutoff)
        self.predictors = predictors
        self.vol = volSeed
        self.volInvTau = np.float64(1 / (volHL * logTwo))
        self.holdings = initHoldings
        self.alphaWeights = alphaWeights
        self.alphas = self.initialiseAlphas()

    def mdUpdate(self, md):
        super().mdUpdate(md)
        for p in self.predictors:
            p.mdUpdate(md)

        self.updateVolatility()
        self.updateAlphas()
        self.calcHoldings()

    def updateVolatility(self):
        self.vol = np.sqrt(utility.emaUpdate(self.vol ** 2, self.annPctChange ** 2, self.timeDecay, self.volInvTau))
        return

    def updateAlphas(self):
        self.cumAlpha = 0
        for alph in self.alphas:
            alph.onMdhUpdate(self)
            self.cumAlpha += self.alphaWeights[alph.name] * alph.alphaVal
        return

    def calcHoldings(self):
        return

    def initialiseAlphas(self):
        # will need to pass predictor objects in here
        return
