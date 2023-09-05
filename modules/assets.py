from pyConfig import *
from modules import utility


class asset:
    def __init__(self, sym, aggFreq, tickSize, spreadCutoff):
        self.sym = sym
        self.tickSize = float(tickSize)
        self.spreadCutoff = spreadCutoff
        self.aggFreq = aggFreq
        self.initialised = False
        self.log = []

    @staticmethod
    def mdhSane(md, sym, spreadCutoff):
        """
        DataFilters
        """
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
        self.bidPrice = md[f'{self.sym}_bid_price']
        self.askPrice = md[f'{self.sym}_ask_price']
        self.bidSize = md[f'{self.sym}_bid_size']
        self.askSize = md[f'{self.sym}_ask_size']
        self.midPrice = self.midPriceCalc(md[f'{self.sym}_bid_price'], md[f'{self.sym}_ask_price'])
        self.microPrice = self.microPriceCalc(md[f'{self.sym}_bid_price'], md[f'{self.sym}_ask_price'],
                                              md[f'{self.sym}_bid_size'], md[f'{self.sym}_ask_size'])
        self.timestamp = md[f'{self.sym}_end_ts']
        self.symbol = md[f'{self.sym}_symbol']
        return

    def firstSaneUpdate(self, md):
        self.initialised = True
        self.contractChange = True
        self.timeDelta = 0
        self.annPctChange = 0
        self.lastMid = self.midPriceCalc(md[f'{self.sym}_bid_price'], md[f'{self.sym}_ask_price'])
        self.lastTS = md[f'{self.sym}_end_ts']
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
            self.timeDelta = (self.timestamp - self.lastTS).seconds / self.aggFreq
        self.lastTS = self.timestamp
        return

    def annualPctChangeCalc(self):
        if (self.timeDelta == 0) | (self.contractChange):
            self.annPctChange = 0
        else:
            pctChange = (self.midPrice - self.lastMid) / self.lastMid
            self.annPctChange = pctChange * np.sqrt(minsPerYear / self.timeDelta)
        self.lastMid = self.midPrice
        return

    def mdUpdate(self, md):
        if not self.mdhSane(md, self.sym, self.spreadCutoff):
            return
        self.updateContractState(md)

        if not self.initialised:
            self.firstSaneUpdate(md)
        else:
            self.contractChange = self.isContractChange()
            self.decayCalc()
            self.annualPctChangeCalc()
        self.updateLog()
        return

    def updateLog(self):
        thisLog = [self.sym, self.timestamp, self.contractChange, self.bidPrice, self.askPrice, self.midPrice,
                   self.timeDelta, self.annPctChange]
        self.log.append(thisLog)
        return


class traded(asset):
    def __init__(self, sym, cfg, tickSize, spreadCutoff, seeds):
        super(traded, self).__init__(sym, cfg['inputParams']['aggFreq'], tickSize, spreadCutoff)
        self.midPrice = seeds[f'{sym}_midPrice']
        self.vol = seeds[f'Volatility_{sym}_timeDR']
        self.volInvTau = np.float64(1 / (cfg['inputParams']['volHL'] * logTwo))

    def updateVolatility(self):
        self.vol = np.sqrt(
            utility.emaUpdate(self.vol ** 2, (self.annPctChange) ** 2, self.timeDelta, self.volInvTau))
        return

    def updateContractState(self, md):
        super().updateContractState(md)
        self.tradingDate = md[f'{self.sym}_date']
        return

    def firstSaneUpdate(self, md):
        super().firstSaneUpdate(md)
        self.lastTradingDate = md[f'{self.sym}_date']
        return

    def isSessionChange(self):
        if self.lastTradingDate != self.tradingDate:
            self.lastTradingDate = self.tradingDate
            return True
        return False