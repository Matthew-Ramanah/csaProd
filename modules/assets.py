from pyConfig import *
from modules import utility


class asset:
    def __init__(self, sym, target, cfg, seeds, prod):
        self.sym = sym
        self.adjSym = utility.findAdjSym(sym)
        self.tickSize = utility.findTickSize(sym)
        self.effSpread = utility.findEffSpread(sym)
        self.volumeCutoff = cfg['fitParams'][target]['volumeCutoff'][sym]
        self.log = []
        self.vol = seeds[f'{sym}_Volatility']
        self.lastClose = seeds[f'{sym}_close']
        self.lastTS = utility.formatStringToTs(seeds[f'{self.sym}_lastTS'])
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
        if (pd.Timestamp(md[f'{sym}_lastTS']) <= self.lastTS) or math.isnan(md[f'{sym}_close']) or (
                md[f'{sym}_intervalVolume'] < volumeCutoff):
            self.stale = True
            return False
        self.stale = False
        return True

    def updateContractState(self, md):
        self.close = md[f'{self.sym}_close']
        self.timestamp = md[f'{self.sym}_lastTS']
        self.adjustment = self.calcAdjustment(md)
        return

    def maintainContractState(self):
        self.close = self.lastClose
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
        self.lastAdjustment = self.calcAdjustment(md)
        return

    def calcAdjustment(self, md):
        self.adjustment = round(md[f'{self.sym}_close'] - md[f'{self.adjSym}_close'], noDec)
        return

    def isContractChange(self):
        if self.sym == self.adjSym:
            return False
        if self.lastAdjustment != self.adjustment:
            self.lastAdjustment = self.adjustment
            return True
        return False

    def decayCalc(self):
        if self.contractChange:
            self.timeDelta = 0
        else:
            self.timeDelta = 1
        return

    def priceDeltaCalc(self):
        if self.contractChange:
            self.priceDelta = 0
        else:
            self.priceDelta = self.close - self.lastClose
        self.lastClose = self.close
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
        self.priceDeltaCalc()
        self.updateVolatility()
        self.updateLog()
        return

    def updateVolatility(self):
        self.vol = np.sqrt(
            utility.emaUpdate(self.vol ** 2, (self.priceDelta) ** 2, self.timeDelta, self.volInvTau))
        return

    def updateLog(self):
        thisLog = [utility.formatTsToString(self.timestamp), self.contractChange, self.close, self.vol]
        self.log.append(thisLog)
        return


class traded(asset):
    def __init__(self, sym, cfg, seeds, prod):
        super(traded, self).__init__(sym, sym, cfg, seeds, prod)

    def updateContractState(self, md):
        super().updateContractState(md)
        self.intervalVolume = md[f'{self.sym}_intervalVolume']
        return

    def firstSaneUpdate(self, md):
        super().firstSaneUpdate(md)
        self.intervalVolume = md[f'{self.sym}_intervalVolume']
        return
