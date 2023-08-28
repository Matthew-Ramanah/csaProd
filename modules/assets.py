from pyConfig import *
import utility


class asset:
    sym = str()
    tickSize = float()
    spreadCuttoff = float()

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

    def __init__(self, sym, cfg, params, refData, seeds, initHoldings=0):
        super().__init__(sym, params['tickSizes'][sym], params['spreadCutoff'][sym])

        # Params
        totalCapital = cfg['inputParams']['basket']['capitalReq'] * cfg['inputParams']['basket']['leverage']
        notionalPerLot = self.calcNotionalPerLot(refData, sym, self.midPrice)
        self.maxLots = self.calcMaxLots(totalCapital, params['fitParams']['basket'][f'{sym}_notionalAlloc'],
                                        notionalPerLot)
        self.volInvTau = np.float64(1 / (cfg['inputParams']['volHL'] * logTwo))
        self.kappa = params[sym]['alphaWeights']['kappa']
        self.hScaler = cfg['hScalers'][sym]
        self.alphaWeights = params[sym]['alphaWeights']

        # Seeds
        self.vol = seeds[f'Volatility_timeDR_{sym}']
        self.holdings = initHoldings
        self.hOpt = self.convertHoldingsToHOpt(self.holdings, self.maxLots, self.hScaler)

        # Construct Alpha Objects
        self.initialiseAlphas(cfg, params)

    @staticmethod
    def calcMaxLots(totalCapital, notionalAlloc, notionalPerLot):
        return int(totalCapital * notionalAlloc / notionalPerLot)

    @staticmethod
    def calcNotionalPerLot(refData, target, midPrice):
        return refData['notionalMultiplier'][target] * midPrice

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

    def calcBuySellCosts(self):
        self.buyCost = self.askPrice - self.midPrice
        self.sellCost = self.midPrice - self.bidPrice
        return

    def calcVar(self):
        self.var = self.vol ** 2
        return

    def calcHOpt(self):
        self.calcBuySellCosts()
        self.calcVar()
        buyBound = (self.cumAlpha - self.kappa * self.buyCost) / (self.var)
        sellBound = (self.cumAlpha + self.kappa * self.sellCost) / (self.var)

        if self.hOpt < buyBound:
            self.hOpt = buyBound
        elif self.hOpt > sellBound:
            self.hOpt = sellBound

        return self.hOpt

    @staticmethod
    def convertHoldingsToHOpt(holdings, maxLots, hScaler):
        return np.clip(holdings / maxLots, -1, 1) * hScaler

    @staticmethod
    def convertHOptToHoldings(maxLots, hOpt, hScaler):
        return int(maxLots * np.clip(hOpt / hScaler, -1, 1))

    def calcHoldings(self):
        hOpt = self.calcHOpt()
        self.holdings = self.convertHOptToHoldings(self.maxLots, hOpt, self.hScaler)
        return

    def initialiseAlphas(self, cfg, params, predictors):
        # Construct a list of alpha objects
        self.alphas = []

        # Also construct a list of predictor objects so we can update them all prior to alpha calcs
        self.predictors = []
        return
