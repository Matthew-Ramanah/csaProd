from pyConfig import *
from modules import utility


class asset:
    def __init__(self, sym, target, cfg, seeds, timezone, prod):
        self.sym = sym
        self.tickSize = utility.findTickSize(sym)
        self.effSpread = utility.findEffSpread(sym)
        self.volumeCutoff = cfg['fitParams'][target]['volumeCutoff'][sym]
        self.log = []
        self.vol = seeds[f'{sym}_Volatility']
        self.lastMid = seeds[f'{sym}_close']
        self.lastTS = utility.formatTsSeed(seeds[f'{self.sym}_lastTS'], timezone)
        self.volInvTau = np.float64(1 / (cfg['inputParams']['volHL'] * logTwo))
        self.prod = prod
        if self.prod:
            self.initialised = True
        else:
            self.initialised = False
        self.stale = False

    def mdhSane(self, md, sym, volumeCutoff):
        """
        DataFilters
        """
        if (pd.Timestamp(md[f'{sym}_lastTS']) <= self.lastTS) or math.isnan(md[f'{sym}_close']):
            self.stale = True
            return False
        self.stale = False
        return True

    def updateContractState(self, md):
        self.close = md[f'{self.sym}_close']
        self.timestamp = md[f'{self.sym}_lastTS']
        return

    def maintainContractState(self):
        self.midPrice = self.lastClose
        self.timestamp = self.lastTS
        self.contractChange = False
        self.timeDelta = 0
        self.priceDelta = 0
        return

    def firstSaneUpdate(self, md):
        self.initialised = True
        self.contractChange = True
        self.timeDelta = 0
        self.priceDelta = 0
        self.lastClose = md[f'{self.sym}_close']
        self.lastTS = md[f'{self.sym}_lastTS']
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
            self.timeDelta = 1
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
        if not self.mdhSane(md, self.sym, self.volumeCutoff):
            self.maintainContractState()
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

    def updateVolatility(self):
        self.vol = np.sqrt(
            utility.emaUpdate(self.vol ** 2, (self.priceDelta) ** 2, self.timeDelta, self.volInvTau))
        return

    def updateLog(self):
        thisLog = [utility.formatTsToStrig(self.timestamp), self.contractChange, self.close, self.timeDelta]
        self.log.append(thisLog)
        return


class traded(asset):
    def __init__(self, sym, cfg, seeds, timezone, prod):
        super(traded, self).__init__(sym, sym, cfg, seeds, timezone, prod)

    def updateContractState(self, md):
        super().updateContractState(md)
        return

    def firstSaneUpdate(self, md):
        super().firstSaneUpdate(md)
        return
