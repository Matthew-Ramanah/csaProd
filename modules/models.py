import pandas as pd

from pyConfig import *
from modules import utility, alphas, assets


class assetModel():
    tradingDate = pd.Timestamp

    def __init__(self, targetSym, cfg, params, refData, seeds, initHoldings=0):
        self.target = assets.traded(targetSym, cfg, params['tickSizes'][targetSym], params['spreadCutoff'][targetSym],
                                    seeds[targetSym])
        self.seeding = True
        self.log = []

        # Params
        self.kappa = params['alphaWeights']['kappa']
        self.hScaler = cfg['fitParams'][targetSym]['hScaler']
        self.alphaWeights = params['alphaWeights']
        self.tradeSizeCap = cfg['fitParams']['basket']['tradeSizeCaps'][targetSym]
        self.liquidityInvTau = np.float64(1 / (cfg['inputParams']['basket']['execution']['liquidityHL'] * logTwo))
        self.pRate = cfg['inputParams']['basket']['execution']['pRate']
        self.notionalAlloc = cfg['fitParams']['basket']['notionalAllocs'][f'{targetSym}']
        self.notionalMultiplier = refData['notionalMultiplier'][self.target.sym]
        self.totalCapital = cfg['inputParams']['basket']['capitalReq'] * cfg['inputParams']['basket']['leverage']

        # Construct Predictors & Alpha Objects
        self.initialisePreds(cfg, params, seeds)
        self.initialiseAlphas(cfg, params, seeds)

        # Initialisations
        self.updateNotionals()
        self.holdings = initHoldings
        self.hOpt = self.convertHoldingsToHOpt(initHoldings, self.maxLots, self.hScaler)

    def updateNotionals(self):
        self.fxRate = self.calcFxRate()
        self.notionalPerLot = self.calcNotionalPerLot()
        self.maxLots = self.calcMaxLots()
        return

    def calcFxRate(self):
        fx = utility.findNotionalFx(self.target.sym)
        if fx == 'USD':
            return 1
        else:
            return self.predictors[f'{fx}='].midPrice

    def calcNotionalPerLot(self):
        return round(self.notionalMultiplier * self.target.midPrice / self.fxRate, 2)

    def calcMaxLots(self):
        return int(self.totalCapital * self.notionalAlloc / self.notionalPerLot)

    def checkifSeeded(self):
        for pred in self.predictors:
            if not self.predictors[pred].initialised:
                return

        self.seeding = False
        lg.info(f'{self.target.sym} Model Seeded')

        for name in self.alphaDict:
            self.alphaDict[name].firstSaneUpdate()
        self.liquidity = self.calcInstLiquidity()
        return

    def checkDateChange(self, md):
        if md[f'{self.target.sym}_date'] != self.tradingDate:
            self.tradingDate = md[f'{self.target.sym}_date']
            return True
        return False

    def mdUpdate(self, md):
        self.target.mdUpdate(md)
        for pred in self.predictors:
            self.predictors[pred].mdUpdate(md)

        if self.seeding:
            self.checkifSeeded()

        elif self.target.mdhSane(md, self.target.sym, self.target.spreadCutoff):
            self.target.modelUpdate()

            for pred in self.predictors:
                self.predictors[pred].modelUpdate()

            self.updateAlphas()

            if self.checkDateChange(md):
                self.updateNotionals()

            self.calcHoldings()

            self.updateLog()

        return

    def updateAlphas(self):
        self.cumAlpha = 0
        for name in self.alphaDict:
            self.alphaDict[name].onMdhUpdate()
            self.cumAlpha += self.alphaWeights[name] * self.alphaDict[name].alphaVal
        return

    def calcBuySellCosts(self):
        self.buyCost = self.target.askPrice - self.target.midPrice
        self.sellCost = self.target.midPrice - self.target.bidPrice
        return

    def calcVar(self):
        self.var = self.target.vol ** 2
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

        return

    def calcInstLiquidity(self):
        return 0.5 * (self.target.bidSize + self.target.askSize)

    def calcMaxTradeSize(self):
        instLiquidity = self.calcInstLiquidity()
        if self.target.isSessionChange():
            self.liquidity = instLiquidity
        else:
            self.liquidity = utility.emaUpdate(self.liquidity, instLiquidity, self.target.timeDelta,
                                               self.liquidityInvTau)
        self.maxTradeSize = int(np.clip(self.pRate * self.liquidity, 0, self.tradeSizeCap))
        return

    @staticmethod
    def convertHoldingsToHOpt(holdings, maxLots, hScaler):
        if maxLots == 0:
            return 0
        return np.clip(holdings / maxLots, -1, 1) * hScaler

    @staticmethod
    def convertHOptToNormedHoldings(hOpt, hScaler):
        return np.clip(hOpt / hScaler, -1, 1)

    @staticmethod
    def convertNormedToSizedHoldings(maxLots, normedHoldings):
        return int(maxLots * normedHoldings)

    def calcHoldings(self):
        self.calcHOpt()
        self.calcMaxTradeSize()
        self.normedHoldings = self.convertHOptToNormedHoldings(self.hOpt, self.hScaler)
        sizedHoldings = self.convertNormedToSizedHoldings(self.maxLots, self.normedHoldings)
        self.tradeVolume = np.clip(sizedHoldings - self.holdings, -self.maxTradeSize, self.maxTradeSize).astype(int)
        self.holdings += self.tradeVolume
        return

    @staticmethod
    def findPredsNeeded(targetSym, feats):
        # Target
        predsNeeded = [targetSym]

        # Fx needed for notionals calc
        fx = utility.findNotionalFx(targetSym)
        if fx != 'USD':
            predsNeeded.append(f'{fx}=')

        # Any symbols used in features
        for ft in feats:
            ftType = ft.split('_')[-3]
            pred = utility.findFeatPred(ft, targetSym)
            if ftType in ['Move', 'VSR']:
                predsNeeded.append(pred)

            elif ftType == 'Basis':
                predsNeeded.append(pred)
                predsNeeded.append(utility.findBasisFrontSym(pred))

        return predsNeeded

    def initialisePreds(self, cfg, params, seeds):
        self.predictors = {}
        predsNeeded = self.findPredsNeeded(self.target.sym, params['feats'])

        for pred in list(set(predsNeeded)):
            self.predictors[pred] = assets.asset(pred, cfg['inputParams']['aggFreq'], params['tickSizes'][pred],
                                                 params['spreadCutoff'][pred], cfg['inputParams']['volHL'],
                                                 seeds[self.target.sym])
        return

    def initialiseAlphas(self, cfg, params, seeds):
        self.alphaDict = {}
        for ft in params['feats']:
            name = ft.replace('feat_', '')
            ftType = ft.split('_')[-3]
            pred = utility.findFeatPred(ft, self.target.sym)
            hl = int(ft.split('_')[-1])
            volHL = cfg['inputParams']['volHL']
            zSeed = seeds[self.target.sym][f'{name}_zSeed']
            smoothSeed = seeds[self.target.sym][f'{name}_smoothSeed']
            volSeed = seeds[self.target.sym][f'{name}_volSeed']
            ncc = params['NCCs'][ft]

            if ftType == 'Move':
                self.alphaDict[name] = alphas.move(self.target, self.predictors[pred], name, hl, zSeed, smoothSeed,
                                                   volHL, volSeed, ncc, False)
            elif ftType == 'VSR':
                self.alphaDict[name] = alphas.vsr(self.target, self.predictors[pred], name, hl, zSeed, smoothSeed,
                                                  volHL, volSeed, ncc, False)
            elif ftType == "Basis":
                frontSym = utility.findBasisFrontSym(pred)
                self.alphaDict[name] = alphas.basis(self.target, self.predictors[pred], name, hl, zSeed, smoothSeed,
                                                    volHL, volSeed, ncc, False, self.predictors[frontSym])
            else:
                lg.info(f'{ftType} Alpha Type Not Found')

        return

    def updateLog(self):
        thisLog = [self.target.timestamp, self.target.contractChange, self.target.bidPrice, self.target.askPrice,
                   self.target.midPrice, self.target.timeDelta, self.target.vol, self.target.midDelta,
                   self.cumAlpha, self.hOpt, self.holdings, self.tradeVolume, self.buyCost, self.sellCost,
                   self.maxTradeSize, self.normedHoldings, self.maxLots, self.notionalPerLot, self.fxRate]
        self.log.append(thisLog)
        return
