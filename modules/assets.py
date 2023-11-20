from pyConfig import *
from modules import utility


class asset:
    def __init__(self, sym, aggFreq, tickSize, spreadCutoff, volHL, seeds, prod):
        self.sym = sym
        self.tickSize = float(tickSize)
        self.spreadCutoff = spreadCutoff
        self.aggFreq = aggFreq
        self.initialised = False
        self.log = []
        self.midPrice = seeds[f'{sym}_midPrice']
        self.vol = seeds[f'Volatility_{sym}']
        self.volInvTau = np.float64(1 / (volHL * logTwo))
        self.prod = prod

    @staticmethod
    def mdhSane(md, sym, spreadCutoff, prod):
        """
        DataFilters
        """
        if not prod:
            if md[f'{sym}_bid_price'] >= md[f'{sym}_ask_price']:
                return False
            if (md[f'{sym}_bid_size'] == 0) | (md[f'{sym}_ask_size'] == 0):
                return False
            if (md[f'{sym}_bid_price'] == 0) | (md[f'{sym}_ask_price'] == 0):
                return False
            if math.isnan(md[f'{sym}_bid_price']) | math.isnan(md[f'{sym}_ask_price']):
                return False
            if (md[f'{sym}_ask_price'] - md[f'{sym}_bid_price']) > spreadCutoff:
                return False
            return True
        else:
            # TODO - Check if timestamp matches most recent hour, throw out if not
            if math.isnan(md[f'{sym}_midPrice']):
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

    def updateContractState(self, md):
        self.midPrice = md[f'{self.sym}_midPrice']
        self.timestamp = md[f'{self.sym}_lastTS']
        self.symbol = md[f'{self.sym}_symbol']
        # self.bidPrice = md[f'{self.sym}_bid_price']
        # self.askPrice = md[f'{self.sym}_ask_price']
        # self.bidSize = md[f'{self.sym}_bid_size']
        # self.askSize = md[f'{self.sym}_ask_size']
        return

    def firstSaneUpdate(self, md):
        self.initialised = True
        self.contractChange = True
        self.timeDelta = 0
        self.midDelta = 0
        self.lastMid = md[f'{self.sym}_midPrice']
        self.lastTS = md[f'{self.sym}_lastTS']
        self.lastSymbol = md[f'{self.sym}_symbol']
        return

    def isContractChange(self):
        if self.lastSymbol != self.symbol:
            self.lastSymbol = self.symbol
            return True
        return False

    def decayCalc(self):
        if self.contractChange:
            self.timeDelta = 0
        else:
            self.timeDelta = 1  # (self.timestamp - self.lastTS).seconds / self.aggFreq
        self.lastTS = self.timestamp
        return

    def midDeltaCalc(self):
        if self.contractChange:
            self.midDelta = 0
        else:
            self.midDelta = self.midPrice - self.lastMid
        self.lastMid = self.midPrice
        return

    def _annualPctChangeCalc(self):
        """
        Deprecated for now
        """
        if (self.timeDelta == 0) | (self.contractChange):
            self.annPctChange = 0
        else:
            pctChange = (self.midPrice - self.lastMid) / self.lastMid
            self.annPctChange = pctChange * np.sqrt(minsPerYear / self.timeDelta)
        self.lastMid = self.midPrice
        return

    def mdUpdate(self, md):
        if not self.mdhSane(md, self.sym, self.spreadCutoff, self.prod):
            return
        if not self.initialised:
            self.firstSaneUpdate(md)
        self.updateContractState(md)
        return

    def modelUpdate(self):
        self.contractChange = self.isContractChange()
        self.decayCalc()
        self.midDeltaCalc()
        self.updateVolatility()
        self.updateLog()
        return

    def updateLog(self):
        thisLog = [self.symbol, self.timestamp, self.contractChange, self.midPrice, self.timeDelta]
        self.log.append(thisLog)
        return

    def updateVolatility(self):
        self.vol = np.sqrt(
            utility.emaUpdate(self.vol ** 2, (self.midDelta) ** 2, self.timeDelta, self.volInvTau))
        return


class traded(asset):
    def __init__(self, sym, cfg, tickSize, spreadCutoff, seeds, prod):
        super(traded, self).__init__(sym, cfg['inputParams']['aggFreq'], tickSize, spreadCutoff,
                                     cfg['inputParams']['volHL'], seeds, prod)

    def updateContractState(self, md):
        super().updateContractState(md)
        return

    def firstSaneUpdate(self, md):
        super().firstSaneUpdate(md)
        return
