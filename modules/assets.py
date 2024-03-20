from pyConfig import *
from modules import utility


class asset:
    def __init__(self, sym, target, cfg, seeds, prod):
        self.sym = sym
        self.tickSize = utility.findTickSize(sym)
        self.effSpread = utility.findEffSpread(sym)
        self.volumeCutoff = cfg['fitParams'][target]['volumeCutoff'][sym]
        self.log = []
        self.vol = seeds[f'{sym}_Volatility']
        self.lastClose = seeds[f'{sym}_close']
        self.lastTS = utility.formatStringToTs(seeds[f'{self.sym}_lastTS'])
        self.volInvTau = np.float64(1 / (cfg['inputParams']['volHL'] * logTwo))
        self.prod = prod
        if prod:
            self.initialised = True
        else:
            self.initialised = False
        self.stale = False

    def mdhSane(self, md):
        """
        DataFilters
        """
        if md[f'{self.sym}_lastTS'] == self.lastTS or md[f'{self.sym}_intervalVolume'] < self.volumeCutoff:
            self.stale = True
            return False
        self.stale = False
        return True

    def updateContractState(self, md):
        self.close = md[f'{self.sym}_close']
        self.lastTS = md[f'{self.sym}_lastTS']
        return

    def maintainContractState(self):
        self.close = self.lastClose
        self.timeDelta = 0
        self.priceDelta = 0
        return

    def firstSaneUpdate(self, md):
        self.initialised = True
        self.timeDelta = 0
        self.priceDelta = 0
        self.lastClose = md[f'{self.sym}_close']
        return

    def decayCalc(self):
        self.timeDelta = 1
        return

    def priceDeltaCalc(self):
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
        thisLog = [utility.formatTsToString(self.lastTS), self.stale, self.close, self.vol]
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
