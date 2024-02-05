from pyConfig import *
from modules import utility, alphas, assets


class assetModel():
    def __init__(self, targetSym, cfg, params, seeds, initHoldings, riskLimits, prod=False):
        self.target = assets.traded(targetSym, cfg, seeds[targetSym], prod)
        self.log = []
        self.alphasLog = []

        self.staleAssets = []
        self.contractChanges = []
        self.prod = prod
        if self.prod:
            self.seeding = False
        else:
            self.seeding = True

        # Params
        self.kappa = params['alphaWeights']['kappa']
        self.hScaler = cfg['fitParams'][targetSym]['hScaler']
        self.alphaWeights = params['alphaWeights']
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
        return

    def calcFxRate(self):
        fx = utility.findNotionalFx(self.target.sym)
        if fx == 'USD':
            return 1
        else:
            fxSym = utility.findFxSym(fx)
            return self.predictors[fxSym].lastClose

    def calcNotionalPerLot(self):
        return int(self.notionalMultiplier * self.target.lastClose * self.fxRate)

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

    def checkContractChanges(self):
        self.contractChanges = []
        if self.target.contractChange:
            self.contractChanges.append(self.target.sym)
        for pred in self.predictors:
            if self.predictors[pred].contractChange:
                self.contractChanges.append(self.predictors[pred].sym)
        return

    def mdUpdate(self, md):
        self.target.mdUpdate(md)
        for pred in self.predictors:
            self.predictors[pred].mdUpdate(md)

        if self.seeding:
            self.checkifSeeded()

        elif not self.target.stale:
            self.target.modelUpdate(md)

            for pred in self.predictors:
                self.predictors[pred].modelUpdate(md)

            self.updateAlphas()

            if self.checkDateChange(md):
                self.updateNotionals()

            self.calcHoldings()
            self.constructLogs()

        else:
            self.tradeVolume = 0
            self.liquidityCap = 0
            self.convertHOptToNormedHoldings()
            self.log.append([])
            self.alphasLog.append([])

        self.checkStaleAssets()
        self.checkContractChanges()
        self.updateSeeds()

        return

    def updateAlphas(self):
        self.cumAlpha = 0
        for name in self.alphaDict:
            self.alphaDict[name].onMdhUpdate()
            self.cumAlpha += self.alphaWeights[name] * self.alphaDict[name].alphaVal
        return

    def calcVar(self):
        self.var = self.target.vol ** 2
        return

    def calcHOpt(self):
        self.calcVar()
        tCost = self.kappa * 0.5 * self.target.effSpread
        buyBound = (self.cumAlpha - tCost) / self.var
        sellBound = (self.cumAlpha + tCost) / self.var

        if self.hOpt < buyBound:
            self.hOpt = buyBound
        elif self.hOpt > sellBound:
            self.hOpt = sellBound

        return

    def calcLiquidityCap(self):
        self.liquidityCap = int(np.clip(self.pRate * self.target.liquidity, 1, self.riskLimits['maxTradeSize']))
        return

    def convertHOptToNormedHoldings(self):
        self.normedHoldings = np.clip(self.hOpt / self.hScaler, -1, 1)
        return

    @staticmethod
    def convertHoldingsToHOpt(holdings, maxPosition, hScaler):
        if maxPosition == 0:
            return 0
        return np.clip(holdings / maxPosition, -1, 1) * hScaler


    def calcTradeVolume(self):
        sizedHoldings = int(self.maxPosition * self.normedHoldings)
        self.tradeVolume = int(np.clip(sizedHoldings - self.initHoldings, -self.liquidityCap, self.liquidityCap))
        return

    def calcHoldings(self):
        self.calcHOpt()
        self.convertHOptToNormedHoldings()
        self.calcLiquidityCap()
        self.calcTradeVolume()
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
            thisLog = [name, utility.formatTsToString(self.target.lastTS), thisAlpha.rawVal, thisAlpha.smoothVal,
                       thisAlpha.zVal, thisAlpha.vol, thisAlpha.featVal, thisAlpha.alphaVal]
            self.alphasLog.append(thisLog)
        return

    def constructLogs(self):
        self.constructAlphasLog()
        thisLog = [utility.formatTsToString(self.target.lastTS), self.target.contractChange, self.target.close,
                   self.target.timeDelta, self.target.vol, self.target.priceDelta, self.cumAlpha, self.normedHoldings,
                   self.initHoldings, self.tradeVolume, self.liquidityCap, self.target.liquidity, self.maxPosition,
                   self.notionalPerLot, self.fxRate]
        self.log.append(thisLog)
        return

    def updateSeeds(self):
        self.seedDump = {f"{self.target.sym}_close": self.target.close,
                         f"{self.target.sym}_Volatility": self.target.vol,
                         f"{self.target.sym}_lastTS": self.target.lastTS.strftime('%Y_%m_%d_%H'),
                         f"{self.target.sym}_Liquidity": self.target.liquidity}

        for pred in self.predictors:
            self.seedDump[f'{pred}_close'] = self.predictors[pred].close
            self.seedDump[f'{pred}_Volatility'] = self.predictors[pred].vol
            self.seedDump[f'{pred}_lastTS'] = self.predictors[pred].lastTS.strftime('%Y_%m_%d_%H')

        for name in self.alphaDict:
            self.seedDump[f'{name}_smoothSeed'] = self.alphaDict[name].smoothVal
            self.seedDump[f'{name}_zSeed'] = self.alphaDict[name].zVal
            self.seedDump[f'{name}_volSeed'] = self.alphaDict[name].vol
        return
