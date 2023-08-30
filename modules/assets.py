from pyConfig import *
from modules import utility, alphas


class asset:
    symbol = str()

    def __init__(self, sym, tickSize, spreadCutoff):
        self.sym = sym
        self.tickSize = float(tickSize)
        self.spreadCuttoff = spreadCutoff
        self.initialised = False
        self.contractChange = True

    def mdUpdate(self, md):
        # Data Filters
        if self.mdhSane(md):
            self.initialised = True

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
            lg.info(f'{self.sym} ContractChange Flagged')
            return True
        return False

    def decayCalc(self, md):
        if self.contractChange:
            self.timeDecay = 0
            return

        self.timeDecay = (md[f'{self.sym}_end_ts'] - self.lastTS).seconds / aggFreq
        return

    def annualPctChangeCalc(self):
        if self.timeDecay == 0:
            self.annPctChange = 0
            return 0

        pctChange = (self.thisMid - self.midPrice) / self.thisMid
        self.annPctChange = pctChange * np.sqrt(1 / self.timeDecay)

        return


class traded(asset):
    log = []

    def __init__(self, sym, cfg, params, refData, seeds, initHoldings=0):
        super().__init__(sym, params['tickSizes'][sym], params['spreadCutoff'][sym])
        self.seeding = True
        self.midPrice = seeds[f'{sym}_midPrice']

        # Params
        totalCapital = cfg['inputParams']['basket']['capitalReq'] * cfg['inputParams']['basket']['leverage']
        notionalPerLot = self.calcNotionalPerLot(refData, sym, self.midPrice)
        self.maxLots = self.calcMaxLots(totalCapital, cfg['fitParams']['basket'][f'{sym}_notionalAlloc'],
                                        notionalPerLot)
        self.volInvTau = np.float64(1 / (cfg['inputParams']['volHL'] * logTwo))
        self.kappa = params['alphaWeights']['kappa']
        self.hScaler = cfg['fitParams']['hScalers'][sym]
        self.alphaWeights = params['alphaWeights']

        # Seeds
        self.vol = seeds[f'Volatility_{sym}_timeDR']
        self.holdings = initHoldings
        self.hOpt = self.convertHoldingsToHOpt(self.holdings, self.maxLots, self.hScaler)

        # Construct Predictors & Alpha Objects
        self.initialisePreds(params)
        self.initialiseAlphas(cfg, params, seeds)

    @staticmethod
    def calcMaxLots(totalCapital, notionalAlloc, notionalPerLot):
        return int(totalCapital * notionalAlloc / notionalPerLot)

    @staticmethod
    def calcNotionalPerLot(refData, target, midPrice):
        return refData['notionalMultiplier'][target] * midPrice

    def checkifSeeded(self):
        for pred in self.predictors:
            if not self.predictors[pred].initialised:
                return
        self.seeding = False
        lg.info(f'{self.sym} Successfully Seeded')

        # Make sure first tick after seeding is flagged as a contractChange
        for pred in self.predictors:
            self.predictors[pred].symbol = ''
        return

    def mdUpdate(self, md):
        if self.seeding:
            self.checkifSeeded()

        super().mdUpdate(md)
        for pred in self.predictors:
            self.predictors[pred].mdUpdate(md)

        if self.mdhSane(md) and not self.seeding:
            self.updateVolatility()
            self.updateAlphas()
            self.calcHoldings()
            self.updateLog()
        return

    def updateVolatility(self):
        self.vol = np.sqrt(utility.emaUpdate(self.vol ** 2, (self.annPctChange) ** 2, self.timeDecay, self.volInvTau))
        return

    def updateAlphas(self):
        self.cumAlpha = 0
        for alph in self.alphaList:
            alph.onMdhUpdate()
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

    @staticmethod
    def findPredsNeeded(targetSym, feats):
        predsNeeded = [targetSym]
        for ft in feats:
            type = ft.split('_')[3]
            if type in ['Move', 'Acc', 'RV', 'AccRV']:
                predsNeeded.append(ft.split('_')[2])

            elif type in ['Basis', 'AccBasis']:
                backSym = ft.split('_')[2]
                predsNeeded.append(backSym)
                predsNeeded.append(utility.findBasisFrontSym(backSym))

        return predsNeeded

    def initialisePreds(self, params):
        self.predictors = {}
        predsNeeded = self.findPredsNeeded(self.sym, params['feats'])

        for pred in list(set(predsNeeded)):
            self.predictors[pred] = asset(pred, params['tickSizes'][pred], params['spreadCutoff'][pred])
        return

    def initialiseAlphas(self, cfg, params, seeds):
        self.alphaList = []
        for ft in params['feats']:
            name = ft.replace('feat_', '')
            ftType = ft.split('_')[3]
            pred = ft.split('_')[2]
            zHL = int(ft.split('_')[-1])
            smoothFactor = cfg['inputParams']['feats']['smoothFactor']
            volHL = cfg['inputParams']['volHL']
            zSeed = seeds[f'{name}_zSeed']
            smoothSeed = seeds[f'{name}_smoothSeed']
            volSeed = seeds[f'{name}_volSeed']
            ncc = params['NCCs'][ft]

            if ftType == 'Move':
                self.alphaList.append(
                    alphas.move(self, self.predictors[pred], name, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed,
                                ncc, False))
            elif ftType == 'Acc':
                self.alphaList.append(
                    alphas.move(self, self.predictors[pred], name, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed,
                                ncc, True))
            elif ftType == 'RV':
                self.alphaList.append(
                    alphas.rv(self, self.predictors[pred], name, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed,
                              ncc, False))
            elif ftType == 'AccRV':
                self.alphaList.append(
                    alphas.rv(self, self.predictors[pred], name, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed,
                              ncc, True))
            elif "Basis" in ftType:
                frontSym = utility.findBasisFrontSym(pred)
                if ftType == 'Basis':
                    self.alphaList.append(
                        alphas.basis(self, self.predictors[pred], name, zHL, zSeed, smoothFactor, smoothSeed, volHL,
                                     volSeed, ncc, False, self.predictors[frontSym]))

                elif ftType == 'AccBasis':
                    self.alphaList.append(
                        alphas.basis(self, self.predictors[pred], name, zHL, zSeed, smoothFactor, smoothSeed, volHL,
                                     volSeed, ncc, True, self.predictors[frontSym]))
            else:
                lg.info(f'{ftType} Alpha Type Not Found')

        return

    def updateLog(self):
        thisLog = [self.lastTS, self.symbol, self.bidPrice, self.askPrice, self.bidSize, self.askPrice, self.midPrice,
                   self.microPrice, self.timeDecay, self.vol, self.annPctChange, self.cumAlpha, self.hOpt,
                   self.holdings]
        self.log.append(thisLog)
        return
