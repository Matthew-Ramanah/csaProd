from pyConfig import *
from modules import utility, alphas, assets


class assetModel():
    def __init__(self, targetSym, cfg, params, refData, seeds, initHoldings=0):
        self.target = assets.traded(targetSym, cfg, params['tickSizes'][targetSym], params['spreadCutoff'][targetSym],
                                    seeds)
        self.seeding = True
        self.log = []

        # Params
        totalCapital = cfg['inputParams']['basket']['capitalReq'] * cfg['inputParams']['basket']['leverage']
        notionalPerLot = self.calcNotionalPerLot(refData, targetSym, seeds[f'{targetSym}_midPrice'])
        self.maxLots = self.calcMaxLots(totalCapital, cfg['fitParams']['basket'][f'{targetSym}_notionalAlloc'],
                                        notionalPerLot)
        self.kappa = params['alphaWeights']['kappa']
        self.hScaler = cfg['fitParams']['hScalers'][targetSym]
        self.alphaWeights = params['alphaWeights']
        self.tradeSizeCap = cfg['fitParams']['tradeSizeCaps'][targetSym]
        self.liquidityInvTau = np.float64(1 / (cfg['inputParams']['basket']['execution']['liquidityHL'] * logTwo))
        self.pRate = cfg['inputParams']['basket']['execution']['pRate']

        # Seeds
        self.holdings = initHoldings
        self.hOpt = self.convertHoldingsToHOpt(initHoldings, self.maxLots, self.hScaler)

        # Construct Predictors & Alpha Objects
        self.initialisePreds(cfg, params)
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
        lg.info(f'{self.target.sym} Model Successfully Seeded')

        for name in self.alphaDict:
            self.alphaDict[name].firstSaneUpdate()
        self.liquidity = self.calcInstLiquidity()
        return

    def mdUpdate(self, md):
        self.target.mdUpdate(md)
        for pred in self.predictors:
            self.predictors[pred].mdUpdate(md)

        if self.seeding:
            self.checkifSeeded()

        elif self.target.mdhSane(md, self.target.sym, self.target.spreadCutoff):
            self.target.updateVolatility()
            self.updateAlphas()
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
        self.maxTradeSize = np.clip(self.pRate * self.liquidity, 0, self.tradeSizeCap)
        return

    @staticmethod
    def convertHoldingsToHOpt(holdings, maxLots, hScaler):
        return np.clip(holdings / maxLots, -1, 1) * hScaler

    @staticmethod
    def convertHOptToHoldings(maxLots, hOpt, hScaler):
        return int(maxLots * np.clip(hOpt / hScaler, -1, 1))

    def calcHoldings(self):
        self.calcHOpt()
        self.calcMaxTradeSize()
        sizedHoldings = self.convertHOptToHoldings(self.maxLots, self.hOpt, self.hScaler)
        self.tradeVolume = np.clip(sizedHoldings - self.holdings, -self.maxTradeSize, self.maxTradeSize).astype(int)
        self.holdings += self.tradeVolume
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

    def initialisePreds(self, cfg, params):
        self.predictors = {}
        predsNeeded = self.findPredsNeeded(self.target.sym, params['feats'])

        for pred in list(set(predsNeeded)):
            self.predictors[pred] = assets.asset(pred, cfg['inputParams']['aggFreq'], params['tickSizes'][pred],
                                                 params['spreadCutoff'][pred])
        return

    def initialiseAlphas(self, cfg, params, seeds):
        self.alphaDict = {}
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
                self.alphaDict[name] = alphas.move(self.target, self.predictors[pred], name, zHL, zSeed, smoothFactor,
                                                   smoothSeed, volHL, volSeed, ncc, False)
            elif ftType == 'Acc':
                self.alphaDict[name] = alphas.move(self.target, self.predictors[pred], name, zHL, zSeed, smoothFactor,
                                                   smoothSeed, volHL, volSeed, ncc, True)
            elif ftType == 'RV':
                self.alphaDict[name] = alphas.rv(self.target, self.predictors[pred], name, zHL, zSeed, smoothFactor,
                                                 smoothSeed, volHL, volSeed, ncc, False)
            elif ftType == 'AccRV':
                self.alphaDict[name] = alphas.rv(self.target, self.predictors[pred], name, zHL, zSeed, smoothFactor,
                                                 smoothSeed, volHL, volSeed, ncc, True)
            elif "Basis" in ftType:
                frontSym = utility.findBasisFrontSym(pred)
                if ftType == 'Basis':
                    self.alphaDict[name] = alphas.basis(self.target, self.predictors[pred], name, zHL, zSeed,
                                                        smoothFactor,
                                                        smoothSeed, volHL, volSeed, ncc, False,
                                                        self.predictors[frontSym])

                elif ftType == 'AccBasis':
                    self.alphaDict[name] = alphas.basis(self.target, self.predictors[pred], name, zHL, zSeed,
                                                        smoothFactor,
                                                        smoothSeed, volHL, volSeed, ncc, True,
                                                        self.predictors[frontSym])
            else:
                lg.info(f'{ftType} Alpha Type Not Found')

        return

    def updateLog(self):
        thisLog = [self.target.timestamp, self.target.contractChange, self.target.bidPrice, self.target.askPrice,
                   self.target.midPrice, self.target.timeDelta, self.target.vol, self.target.annPctChange,
                   self.cumAlpha, self.hOpt, self.holdings, self.tradeVolume]
        self.log.append(thisLog)
        return
