from pyConfig import *
from modules import utility


class alpha:
    def __init__(self, target, name, hl, zSeed, smoothSeed, volHL, volSeed, ncc):
        self.target = target
        self.name = name
        self.zInvTau = np.float64(1 / (scoreFactor * hl * logTwo))
        self.zVal = zSeed
        self.smoothInvTau = np.float64(1 / (hl * logTwo))
        self.smoothVal = smoothSeed
        self.lastSmoothVal = smoothSeed
        self.volInvTau = np.float64(1 / (volHL * logTwo))
        self.vol = volSeed
        self.ncc = ncc
        self.log = []

    def firstSaneUpdate(self):
        """
        May get overloaded
        """
        return

    def onMdhUpdate(self):
        self.decayCalc()
        self.calcRawVal()
        self.updateSmoothVal()
        self.updateZVal()
        self.updateVolatility()
        self.updateFeatVal()
        self.updateAlphaVal()
        self.updateLog()
        return

    def decayCalc(self):
        """
        May get overloaded
        """
        self.decay = self.target.timeDelta
        return

    def calcRawVal(self):
        """
        Should always get overloaded
        """
        lg.info(f"{self.name} Has No RawVal Calc, Keeping it at 0")
        self.rawVal = 0
        return

    def updateSmoothVal(self):
        self.smoothVal = utility.emaUpdate(self.smoothVal, self.rawVal, self.decay, self.smoothInvTau)
        return

    def updateZVal(self):
        self.zVal = utility.emaUpdate(self.zVal, self.smoothVal, self.decay, self.zInvTau)
        return

    def updateVolatility(self):
        self.vol = np.sqrt(utility.emaUpdate(self.vol ** 2, self.zVal ** 2, self.decay, self.volInvTau))
        return

    def updateFeatVal(self):
        self.featVal = np.clip(self.zVal / self.vol, -signalCap, signalCap)
        return

    def updateAlphaVal(self):
        self.alphaVal = self.ncc * self.featVal * self.target.vol
        return

    def updateLog(self):
        thisLog = [self.target.lastTS, self.decay, self.rawVal, self.smoothVal, self.zVal, self.vol, self.featVal]
        self.log.append(thisLog)
        return


class move(alpha):
    def __init__(self, target, predictor, name, hl, zSeed, smoothSeed, volHL, volSeed, ncc):
        super().__init__(target, name, hl, zSeed, smoothSeed, volHL, volSeed, ncc)
        self.predictor = predictor

    def calcRawVal(self):
        self.rawVal = self.predictor.priceDelta / self.predictor.vol
        return


class vsr(alpha):
    def __init__(self, target, pred1, pred2, name, hl, zSeed, smoothSeed, volHL, volSeed, ncc):
        super().__init__(target, name, hl, zSeed, smoothSeed, volHL, volSeed, ncc)
        self.pred1 = pred1
        self.pred2 = pred2

    def calcRawVal(self):
        self.rawVal = self.pred1.priceDelta / self.pred1.vol - self.pred2.priceDelta / self.pred2.vol
        return
