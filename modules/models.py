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
        self.pRate = cfg['inputParams']['basket']['execution']['pRate']
        self.notionalAlloc = cfg['fitParams']['basket']['notionalAllocs'][f'{targetSym}']
        self.notionalMultiplier = utility.findNotionalMultiplier(targetSym)
        self.totalCapital = cfg['inputParams']['basket']['capitalReq'] * cfg['inputParams']['basket']['leverage']
        self.riskLimits = riskLimits[targetSym]
        self.noTradeHours = cfg['inputParams']['noTradeHours'] + [cfg['fitParams'][targetSym]['closeTime']]

        # Construct Predictors & Alpha Objects
        self.initialisePreds(cfg, seeds)
        self.initialiseAlphas(cfg, params, seeds)

        # Initialisations
        self.lastCumVol = seeds[targetSym][f'{targetSym}_cumDailyVolume']
        self.updateNotionals()
        self.initHoldings = self.assertLotSizeHoldings(cfg, initHoldings)
        self.h0 = self.convertHoldingsToHOpt(self.initHoldings, self.maxPosition)

        return

    def assertLotSizeHoldings(self, cfg, initHoldings):
        if cfg['investor'] == 'AFBI':
            return initHoldings
        elif cfg['investor'] == 'Qube':
            return round(initHoldings / self.notionalPerLot)
        else:
            raise ValueError(f"No {cfg['investor']} Holdings Logic Implemented")

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

    def checkSessionChange(self, md):
        thisCumVol = md[f'{self.target.sym}_cumDailyVolume']
        if thisCumVol < self.lastCumVol:
            seshChange = True
        else:
            seshChange = False
        self.lastCumVol = thisCumVol
        return seshChange

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

        elif not self.target.stale:
            self.target.modelUpdate(md)

            for pred in self.predictors:
                self.predictors[pred].modelUpdate(md)

            self.updateAlphas()

            if self.checkSessionChange(md):
                self.updateNotionals()

            self.calcHoldings(md)
            self.constructLogs()

        else:
            self.tradeVolume = 0
            self.maxTradeSize = 0
            self.hOpt = self.h0
            self.log.append([])
            self.alphasLog.append([])

        self.calcNativeTargetNotional()
        self.checkStaleAssets()
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

    def checkNoTradeZone(self, md):
        if int(md['timeSig'][-2:]) in self.noTradeHours:
            self.noTradeZone = True
            self.maxTradeSize = 0
            self.tradeVolume = 0
        else:
            self.noTradeZone = False
        return

    def calcMaxDeltaT(self):
        if self.noTradeZone:
            self.maxDeltaT = 0
        else:
            self.maxDeltaT = maxAssetDelta
        return

    def calcHOpt(self):
        self.calcVar()
        self.calcMaxDeltaT()
        tCost = self.kappa * self.target.effSpread
        buyBound = np.clip((self.cumAlpha - tCost) / (self.var * self.hScaler), -1, 1)
        sellBound = np.clip((self.cumAlpha + tCost) / (self.var * self.hScaler), -1, 1)

        if self.h0 < buyBound:
            self.hOpt = np.clip(buyBound, self.h0, self.h0 + self.maxDeltaT)
        elif self.h0 > sellBound:
            self.hOpt = np.clip(sellBound, self.h0 - self.maxDeltaT, self.h0)
        else:
            self.hOpt = self.h0

        return

    def calcMaxTradeSize(self):
        self.maxTradeSize = int(np.clip(self.pRate * self.target.liquidity, 1, self.riskLimits['maxTradeSize']))
        return

    @staticmethod
    def convertHoldingsToHOpt(holdings, maxPosition):
        if maxPosition == 0:
            return 0
        return np.clip(holdings / maxPosition, -1, 1)

    def calcTradeVolume(self):
        sizedHoldings = int(self.maxPosition * self.hOpt)
        self.tradeVolume = int(np.clip(sizedHoldings - self.initHoldings, -self.maxTradeSize, self.maxTradeSize))
        return

    def calcNativeTargetNotional(self):
        self.nativeTargetNotional = (self.initHoldings + self.tradeVolume) * self.notionalPerLot / self.fxRate
        return

    def calcHoldings(self, md):
        self.checkNoTradeZone(md)
        self.calcHOpt()
        if not self.noTradeZone:
            self.calcMaxTradeSize()
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
        self.h0 = self.hOpt
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
        thisLog = [utility.formatTsToString(self.target.lastTS), self.lastCumVol, self.target.close,
                   self.target.timeDelta, self.target.vol, self.target.priceDelta, self.cumAlpha, self.hOpt,
                   self.initHoldings, self.tradeVolume, self.maxTradeSize, self.target.liquidity, self.maxPosition,
                   self.notionalPerLot, self.fxRate]
        self.log.append(thisLog)
        return

    def updateSeeds(self):
        self.seedDump = {f"{self.target.sym}_close": self.target.close,
                         f"{self.target.sym}_Volatility": self.target.vol,
                         f"{self.target.sym}_lastTS": self.target.lastTS.strftime('%Y_%m_%d_%H'),
                         f"{self.target.sym}_Liquidity": self.target.liquidity,
                         f"{self.target.sym}_cumDailyVolume": self.lastCumVol}

        for pred in self.predictors:
            self.seedDump[f'{pred}_close'] = self.predictors[pred].close
            self.seedDump[f'{pred}_Volatility'] = self.predictors[pred].vol
            self.seedDump[f'{pred}_lastTS'] = self.predictors[pred].lastTS.strftime('%Y_%m_%d_%H')

        for name in self.alphaDict:
            self.seedDump[f'{name}_smoothSeed'] = self.alphaDict[name].smoothVal
            self.seedDump[f'{name}_zSeed'] = self.alphaDict[name].zVal
            self.seedDump[f'{name}_volSeed'] = self.alphaDict[name].vol
        return
