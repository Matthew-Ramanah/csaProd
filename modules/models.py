from pyConfig import *
from modules import utility, alphas, assets


class assetModel():
    def __init__(self, targetSym, cfg, params, seeds, initHoldings, riskLimits, prod=False):
        self.target = assets.traded(targetSym, cfg, seeds[targetSym], prod)
        self.log = []
        self.alphasLog = []

        self.staleAssets = []
        self.prod = prod
        if self.prod:
            self.seeding = False
        else:
            self.seeding = True

        # Params
        self.kappa = params['alphaWeights']['kappa']
        self.hScaler = cfg['fitParams'][targetSym]['hScaler']
        self.alphaWeights = params['alphaWeights']
        self.liquidityInvTau = np.float64(1 / (cfg['inputParams']['basket']['execution']['liquidityHL'] * logTwo))
        self.pRate = cfg['inputParams']['basket']['execution']['pRate']
        self.notionalAlloc = cfg['fitParams']['basket']['notionalAllocs'][f'{targetSym}']
        self.notionalMultiplier = utility.findNotionalMultiplier(targetSym)
        self.totalCapital = cfg['inputParams']['basket']['capitalReq'] * cfg['inputParams']['basket']['leverage']
        self.riskLimits = riskLimits[targetSym]

        # Construct Predictors & Alpha Objects
        self.initialisePreds(cfg, seeds)
        self.initialiseAlphas(cfg, params, seeds)

        # Initialisations
        self.tradingDate = utility.findTsSeedDate(seeds[targetSym][f'{targetSym}_lastTS'])
        self.updateNotionals()
        self.initHoldings = initHoldings
        self.hOpt = self.convertHoldingsToHOpt(initHoldings, self.maxPosition, self.hScaler)

        return

    def updateNotionals(self):
        self.fxRate = self.calcFxRate()
        self.notionalPerLot = self.calcNotionalPerLot()
        self.maxPosition = self.calcMaxPosition()
        self.calcMaxTradeSize()
        return

    def calcFxRate(self):
        fx = utility.findNotionalFx(self.target.sym)
        if fx == 'USD':
            return 1
        else:
            fxSym = utility.findFxSym(fx)
            return self.predictors[fxSym].lastClose

    def calcNotionalPerLot(self):
        return round(self.notionalMultiplier * self.target.lastClose * self.fxRate, 2)

    def calcMaxPosition(self):
        return min(int(self.totalCapital * self.notionalAlloc / self.notionalPerLot), self.riskLimits['maxPosition'])

    def checkifSeeded(self):
        for pred in self.predictors:
            if not self.predictors[pred].initialised:
                return

        self.seeding = False
        lg.info(f'{self.target.sym} Model Seeded')

        for name in self.alphaDict:
            self.alphaDict[name].firstSaneUpdate()
        return

    def checkDateChange(self, md):
        thisDate = pd.Timestamp(md[f'{self.target.sym}_lastTS']).date()
        if thisDate != self.tradingDate:
            self.tradingDate = thisDate
            return True
        return False

    def checkStaleAssets(self):
        self.staleAssets = []
        if self.target.stale:
            self.staleAssets.append(self.target.sym)
        for pred in self.predictors:
            if self.predictors[pred].stale:
                self.staleAssets.append(self.predictors[pred].sym)
        return

    def mdUpdate(self, md):
        self.target.mdUpdate(md)
        for pred in self.predictors:
            self.predictors[pred].mdUpdate(md)

        if self.seeding:
            self.checkifSeeded()

        elif self.target.mdhSane(md, self.target.sym, self.target.volumeCutoff):
            self.target.modelUpdate()

            for pred in self.predictors:
                self.predictors[pred].modelUpdate()

            self.updateAlphas()

            if self.checkDateChange(md):
                self.updateNotionals()

            self.calcHoldings()
            self.constructLogs()

        else:
            self.tradeVolume = 0
            self.log.append([])
            self.alphasLog.append([])

        self.checkStaleAssets()
        self.updateSeeds()

        return

    def updateAlphas(self):
        self.cumAlpha = 0
        for name in self.alphaDict:
            self.alphaDict[name].onMdhUpdate()
            self.cumAlpha += self.alphaWeights[name] * self.alphaDict[name].alphaVal
        return

    def calcBuySellCosts(self):
        self.buyCost = self.target.effSpread
        self.sellCost = self.target.effSpread
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

    def calcMaxTradeSize(self):
        self.maxTradeSize = min(int(np.ceil(maxAssetDelta * self.maxPosition)), self.riskLimits['maxTradeSize'])

        """
        Deprecate liquidity filter until we have live bid/ask data
        instLiquidity = self.calcInstLiquidity()
        if self.target.isSessionChange():
            self.liquidity = instLiquidity
        else:
            self.liquidity = utility.emaUpdate(self.liquidity, instLiquidity, self.target.timeDelta,
                                               self.liquidityInvTau)
        self.maxTradeSize = int(np.clip(self.pRate * self.liquidity, 0, self.tradeSizeCap))
        """
        return

    @staticmethod
    def convertHoldingsToHOpt(holdings, maxPosition, hScaler):
        if maxPosition == 0:
            return 0
        return np.clip(holdings / maxPosition, -1, 1) * hScaler

    @staticmethod
    def convertHOptToNormedHoldings(hOpt, hScaler):
        return np.clip(hOpt / hScaler, -1, 1)

    @staticmethod
    def convertNormedToSizedHoldings(maxPosition, normedHoldings):
        return int(maxPosition * normedHoldings)

    def calcHoldings(self):
        self.calcHOpt()
        self.normedHoldings = self.convertHOptToNormedHoldings(self.hOpt, self.hScaler)
        sizedHoldings = self.convertNormedToSizedHoldings(self.maxPosition, self.normedHoldings)
        self.tradeVolume = int(np.clip(sizedHoldings - self.initHoldings, -self.maxTradeSize, self.maxTradeSize))
        if not self.prod:
            self.updateReconPosition()
        return

    def initialisePreds(self, cfg, seeds):
        self.predictors = {}
        predsNeeded = utility.findSymsNeeded(cfg, self.target.sym)

        for pred in list(set(predsNeeded)):
            self.predictors[pred] = assets.asset(pred, self.target.sym, cfg, seeds[self.target.sym], self.prod)
        return

    def initialiseAlphas(self, cfg, params, seeds):
        self.alphaDict = {}
        for ft in params['feats']:
            name = ft.replace('feat_', '')
            ftType = ft.split('_')[-3]
            hl = int(ft.split('_')[-1])
            volHL = cfg['inputParams']['volHL']
            zSeed = seeds[self.target.sym][f'{name}_zSeed']
            smoothSeed = seeds[self.target.sym][f'{name}_smoothSeed']
            volSeed = seeds[self.target.sym][f'{name}_volSeed']
            ncc = params['NCCs'][ft]
            preds = utility.findFtSyms(self.target.sym, ft)

            if ftType == 'Move':
                self.alphaDict[name] = alphas.move(self.target, self.predictors[preds[0]], name, hl, zSeed, smoothSeed,
                                                   volHL, volSeed, ncc)
            elif ftType == 'VSR':
                self.alphaDict[name] = alphas.vsr(self.target, self.predictors[preds[0]], self.predictors[preds[1]],
                                                  name, hl, zSeed, smoothSeed, volHL, volSeed, ncc)
            else:
                lg.info(f'{ftType} Alpha Type Not Found')

        return

    def updateReconPosition(self):
        self.initHoldings += self.tradeVolume
        return

    def constructAlphasLog(self):
        for name in self.alphaDict:
            thisAlpha = self.alphaDict[name]
            thisLog = [name, utility.formatTsToString(self.target.timestamp), thisAlpha.rawVal, thisAlpha.smoothVal,
                       thisAlpha.zVal, thisAlpha.vol, thisAlpha.featVal, thisAlpha.alphaVal]
            self.alphasLog.append(thisLog)
        return

    def constructLogs(self):
        self.constructAlphasLog()
        thisLog = [utility.formatTsToString(self.target.timestamp), self.target.contractChange, self.target.close,
                   self.target.timeDelta, self.target.vol, self.target.priceDelta, self.cumAlpha, self.hOpt,
                   self.initHoldings, self.tradeVolume, self.maxTradeSize, self.normedHoldings, self.maxPosition,
                   self.notionalPerLot, self.fxRate]
        self.log.append(thisLog)
        return

    def updateSeeds(self):
        self.seedDump = {f"{self.target.sym}_close": self.target.close,
                         f"{self.target.sym}_Volatility": self.target.vol,
                         f"{self.target.sym}_lastTS": self.target.timestamp.strftime('%Y_%m_%d_%H')}

        for pred in self.predictors:
            self.seedDump[f'{pred}_close'] = self.predictors[pred].close
            self.seedDump[f'{pred}_Volatility'] = self.predictors[pred].vol
            self.seedDump[f'{pred}_lastTS'] = self.predictors[pred].timestamp.strftime('%Y_%m_%d_%H')

        for name in self.alphaDict:
            self.seedDump[f'{name}_smoothSeed'] = self.alphaDict[name].smoothVal
            self.seedDump[f'{name}_zSeed'] = self.alphaDict[name].zVal
            self.seedDump[f'{name}_volSeed'] = self.alphaDict[name].vol
        return
