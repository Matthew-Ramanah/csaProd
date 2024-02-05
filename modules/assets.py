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
        self.lastAdjustment = seeds[f'{sym}_adjustment']
        self.volInvTau = np.float64(1 / (cfg['inputParams']['volHL'] * logTwo))
        if prod:
            self.initialised = True
        else:
            self.initialised = False
        self.stale = False
        self.contractChange = False

    def mdhSane(self, md):
        """
        DataFilters
        """
        if md[f'{self.sym}_lastTS'] <= self.lastTS or math.isnan(md[f'{self.sym}_close']) or md[
            f'{self.sym}_intervalVolume'] < self.volumeCutoff:
            self.stale = True
            return False
        self.stale = False
        return True

    def updateContractState(self, md):
        self.close = md[f'{self.sym}_close']
        self.lastTS = md[f'{self.sym}_lastTS']
        self.calcAdjustment(md)
        return

    def maintainContractState(self):
        self.close = self.lastClose
        self.adjustment = self.lastAdjustment
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
        self.lastAdjustment = 0.0
        return

    def calcAdjustment(self, md):
        if utility.isAdjSym(self.sym):
            self.adjustment = 0.0
        else:
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
        if not self.mdhSane(md):
            self.maintainContractState()
            return
        if not self.initialised:
            self.firstSaneUpdate(md)
        self.updateContractState(md)
        return

    def modelUpdate(self, md):
        # self.contractChange = self.isContractChange()
        self.decayCalc()
        self.priceDeltaCalc()
        self.updateVolatility()
        self.updateLog()
        return

    def updateVolatility(self):
        self.vol = np.sqrt(
            utility.emaUpdate(self.vol ** 2, self.priceDelta ** 2, self.timeDelta, self.volInvTau))
        return

    def updateLog(self):
        thisLog = [utility.formatTsToString(self.lastTS), self.adjustment, self.close, self.vol]
        self.log.append(thisLog)
        return


class traded(asset):
    def __init__(self, sym, cfg, seeds, prod):
        super(traded, self).__init__(sym, sym, cfg, seeds, prod)
        self.liquidityInvTau = np.float64(1 / (cfg['inputParams']['basket']['execution']['liquidityHL'] * logTwo))
        self.liquidity = seeds[f'{sym}_Liquidity']

    def modelUpdate(self, md):
        super().modelUpdate(md)
        self.updateLiquidity(md)
        return

    def firstSaneUpdate(self, md):
        super().firstSaneUpdate(md)
        self.liquidity = md[f'{self.sym}_intervalVolume']
        return

    def updateLiquidity(self, md):
        self.liquidity = utility.emaUpdate(self.liquidity, md[f'{self.sym}_intervalVolume'], self.timeDelta,
                                           self.liquidityInvTau)
        return
